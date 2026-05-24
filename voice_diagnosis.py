"""
闻诊分析器（基于 Parselmouth / Praat）
输入：音频字节流（任意 Web 可录制格式，ffmpeg 转 wav 后分析）
输出：结构化中医闻诊 JSON，字段严格对齐 persona.md 约定
"""
import io
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional

import numpy as np
import parselmouth
from parselmouth.praat import call


class VoiceDiagnosis:
    """
    闻诊（语声 + 语言节奏）分析器。
    只实现 persona.md 中精简版指标：
      voice: volume, pitch, hoarseness{present,degree}, tremor_present
      speech_rhythm: speed, fluency, breath_pause_frequency
    """

    # ============ 阈值（基于中医声学文献与 Praat 常用基线） ============
    # 音量（基于 Parselmouth to_intensity 的 dB 均值）
    VOL_EXTREME_LOW = 50.0
    VOL_LOW = 60.0
    VOL_NORMAL_HIGH = 70.0  # > 70 为洪亮

    # 基频（F0 均值，单位 Hz）——男女自动标定
    F0_MALE_LOW = 100.0
    F0_MALE_HIGH = 160.0
    F0_FEMALE_LOW = 170.0
    F0_FEMALE_HIGH = 260.0
    F0_GENDER_SPLIT = 160.0  # 均值 < 160 视为男性

    # HNR (谐噪比, dB)：越低越嘶哑
    HNR_SEVERE = 5.0
    HNR_MODERATE = 10.0
    HNR_MILD = 15.0

    # Jitter / Shimmer 异常阈值（局部 local 百分比）
    JITTER_ABNORMAL = 1.04  # %
    JITTER_TREMOR = 1.50  # % 以上视为明显颤
    SHIMMER_ABNORMAL = 3.81  # %

    # 颤抖：F0 标准差（Hz）
    F0_SD_TREMOR = 15.0

    # 语速（音节/秒，粗估：用语音帧计数 / 有声时长）
    SPEED_FAST = 3.5
    SPEED_SLOW = 2.0

    # 停顿
    PAUSE_MANY = 2  # 5 秒内 >= 2 次视为换气偏多

    def __init__(self):
        self.has_ffmpeg = bool(shutil.which("ffmpeg"))
        if not self.has_ffmpeg:
            print("⚠️  未检测到 ffmpeg，将仅支持纯 WAV/AIFF 输入（前端需转码）")
        print("✅ 闻诊分析器初始化完成")

    # ---------------------------------------------------------------- #
    # 入口
    # ---------------------------------------------------------------- #
    def analyze(self, audio_bytes: bytes, original_filename: str = "audio") -> Dict[str, Any]:
        if not audio_bytes:
            raise ValueError("录音内容为空")

        # 快速辨别：RIFF...WAVE 头 → 直接当 wav 喂 parselmouth
        header = audio_bytes[:12]
        is_wav = header[:4] == b"RIFF" and header[8:12] == b"WAVE"

        with tempfile.TemporaryDirectory() as tmp:
            src_path = os.path.join(tmp, f"src_{original_filename}")
            with open(src_path, "wb") as f:
                f.write(audio_bytes)

            if is_wav:
                wav_path = src_path
            else:
                if not self.has_ffmpeg:
                    raise ValueError("服务器未安装 ffmpeg，请让前端上传 WAV 格式")
                wav_path = os.path.join(tmp, "out.wav")
                self._to_wav(src_path, wav_path)

            sound = parselmouth.Sound(wav_path)
            # 单通道 + 重采样 16kHz，去掉直流
            if sound.n_channels > 1:
                sound = sound.convert_to_mono()
            sound = sound.resample(16000)

            duration = sound.get_total_duration()
            if duration < 0.8:
                raise ValueError("录音太短（<0.8s），无法分析，请再录一次")

            # 计算各项特征
            vol_mean_db = self._mean_intensity(sound)
            f0_mean, f0_sd = self._pitch_stats(sound)
            hnr_mean = self._hnr_mean(sound)
            jitter, shimmer = self._jitter_shimmer(sound)
            voiced_seconds, pause_count = self._voiced_and_pauses(sound)

            # 数据分档
            volume_label = self._label_volume(vol_mean_db)
            pitch_label = self._label_pitch(f0_mean)
            hoarseness_present, hoarseness_degree = self._label_hoarseness(hnr_mean, jitter, shimmer)
            tremor_present = self._label_tremor(f0_sd, jitter)
            speed_label = self._label_speed(voiced_seconds, duration)
            fluency_label = self._label_fluency(pause_count, hnr_mean)
            pause_label = self._label_pause_freq(pause_count, duration)

            # 组装结构化结果
            voice_diagnosis = {
                "voice": {
                    "volume": volume_label,
                    "pitch": pitch_label,
                    "hoarseness": {
                        "present": hoarseness_present,
                        "degree": hoarseness_degree,
                    },
                    "tremor_present": tremor_present,
                },
                "speech_rhythm": {
                    "speed": speed_label,
                    "fluency": fluency_label,
                    "breath_pause_frequency": pause_label,
                },
            }

            tcm = self._tcm_diagnosis(voice_diagnosis)

            # 原始数值也回传一份（前端可隐藏，方便调试）
            metrics = {
                "duration_sec": round(duration, 2),
                "intensity_db": round(vol_mean_db, 1),
                "f0_mean_hz": round(f0_mean, 1) if f0_mean else None,
                "f0_sd_hz": round(f0_sd, 1) if f0_sd is not None else None,
                "hnr_db": round(hnr_mean, 1) if hnr_mean is not None else None,
                "jitter_pct": round(jitter, 3) if jitter is not None else None,
                "shimmer_pct": round(shimmer, 3) if shimmer is not None else None,
                "voiced_seconds": round(voiced_seconds, 2),
                "pause_count": pause_count,
            }

            return {
                "voice_diagnosis": voice_diagnosis,
                "tcm_diagnosis": tcm,
                "metrics": metrics,
            }

    # ---------------------------------------------------------------- #
    # 内部工具
    # ---------------------------------------------------------------- #
    @staticmethod
    def _to_wav(src: str, dst: str) -> None:
        """用 ffmpeg 把任意输入转为 16kHz mono WAV。"""
        # ffmpeg 必须存在
        if not shutil.which("ffmpeg"):
            raise ValueError("服务器未安装 ffmpeg，无法解码音频")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", src,
            "-ac", "1", "-ar", "16000",
            dst,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        except subprocess.CalledProcessError as e:
            raise ValueError(f"音频格式无法解码：{e.stderr.decode('utf-8', errors='ignore')[:120]}")

    def _mean_intensity(self, sound: parselmouth.Sound) -> float:
        try:
            intensity = sound.to_intensity(minimum_pitch=75)
            values = intensity.values[0]
            # 过滤掉静音段（-inf / 极低值）
            valid = values[np.isfinite(values) & (values > 30)]
            if len(valid) == 0:
                return 0.0
            return float(np.mean(valid))
        except Exception:
            return 0.0

    def _pitch_stats(self, sound: parselmouth.Sound):
        """返回 (F0 均值, F0 标准差)，只统计 voiced 帧。"""
        try:
            pitch = sound.to_pitch(time_step=0.01, pitch_floor=75.0, pitch_ceiling=500.0)
            arr = pitch.selected_array["frequency"]
            voiced = arr[arr > 0]
            if len(voiced) < 5:
                return 0.0, 0.0
            return float(np.mean(voiced)), float(np.std(voiced))
        except Exception:
            return 0.0, 0.0

    def _hnr_mean(self, sound: parselmouth.Sound) -> Optional[float]:
        try:
            harmonicity = sound.to_harmonicity()
            values = np.asarray(harmonicity.values).flatten()
            valid = values[np.isfinite(values) & (values > -20)]
            if len(valid) == 0:
                return None
            return float(np.mean(valid))
        except Exception:
            return None

    def _jitter_shimmer(self, sound: parselmouth.Sound):
        """Jitter (local %) / Shimmer (local %)。"""
        try:
            point_process = call(sound, "To PointProcess (periodic, cc)", 75.0, 500.0)
            jitter = call(point_process, "Get jitter (local)", 0.0, 0.0, 0.0001, 0.02, 1.3) * 100.0
            shimmer = call(
                [sound, point_process], "Get shimmer (local)", 0.0, 0.0, 0.0001, 0.02, 1.3, 1.6
            ) * 100.0
            j = float(jitter) if jitter == jitter else None  # NaN 过滤
            s = float(shimmer) if shimmer == shimmer else None
            return j, s
        except Exception:
            return None, None

    def _voiced_and_pauses(self, sound: parselmouth.Sound):
        """估算有声时长和停顿次数（基于 Intensity 过阈值）。"""
        try:
            intensity = sound.to_intensity(minimum_pitch=75, time_step=0.01)
            values = np.asarray(intensity.values).flatten()
            # 用分位点定义阈值：低于 30% 分位即视为静音
            if len(values) == 0:
                return 0.0, 0
            finite = values[np.isfinite(values)]
            if len(finite) == 0:
                return 0.0, 0
            threshold = max(40.0, np.percentile(finite, 30))
            voiced_mask = values > threshold
            voiced_seconds = float(np.sum(voiced_mask)) * 0.01

            # 停顿计数：检测静音段 >= 200ms 的次数
            min_pause_frames = 20  # 200ms / 10ms
            pause_count = 0
            run = 0
            for v in voiced_mask:
                if not v:
                    run += 1
                else:
                    if run >= min_pause_frames:
                        pause_count += 1
                    run = 0
            # 末尾不计（录音可能切掉）
            return voiced_seconds, pause_count
        except Exception:
            return 0.0, 0

    # ---------------------------------------------------------------- #
    # 分档逻辑
    # ---------------------------------------------------------------- #
    def _label_volume(self, db: float) -> str:
        if db <= 0:
            return "极微"
        if db < self.VOL_EXTREME_LOW:
            return "极微"
        if db < self.VOL_LOW:
            return "低微"
        if db < self.VOL_NORMAL_HIGH:
            return "正常"
        return "洪亮"

    def _label_pitch(self, f0: float) -> str:
        if f0 <= 0:
            return "未测到"
        # 自动按性别区间判断
        if f0 < self.F0_GENDER_SPLIT:
            # 男性范围
            if f0 < self.F0_MALE_LOW:
                return "低沉"
            if f0 <= self.F0_MALE_HIGH:
                return "正常"
            return "高亢"
        else:
            # 女性范围
            if f0 < self.F0_FEMALE_LOW:
                return "低沉"
            if f0 <= self.F0_FEMALE_HIGH:
                return "正常"
            return "高亢"

    def _label_hoarseness(self, hnr: Optional[float], jitter: Optional[float],
                          shimmer: Optional[float]):
        if hnr is None:
            return False, "无"
        # 综合判定
        is_hoarse = False
        if hnr < self.HNR_MILD:
            is_hoarse = True
        if jitter is not None and jitter > self.JITTER_ABNORMAL:
            is_hoarse = True
        if shimmer is not None and shimmer > self.SHIMMER_ABNORMAL:
            is_hoarse = True

        if not is_hoarse:
            return False, "无"
        if hnr < self.HNR_SEVERE:
            return True, "重度"
        if hnr < self.HNR_MODERATE:
            return True, "中度"
        return True, "轻度"

    def _label_tremor(self, f0_sd: float, jitter: Optional[float]) -> bool:
        if f0_sd >= self.F0_SD_TREMOR:
            return True
        if jitter is not None and jitter >= self.JITTER_TREMOR:
            return True
        return False

    def _label_speed(self, voiced_seconds: float, total_seconds: float) -> str:
        if voiced_seconds <= 0.2:
            return "未测到"
        # 粗略音节率：按"每 0.2s 一个音节"为中速基准（每秒 ~5 个 10ms 帧算一个音节粒度）
        # 这里用有声帧密度做快慢标定
        density = voiced_seconds / max(total_seconds, 0.5)
        if density > 0.75:
            return "偏快"
        if density < 0.45:
            return "偏慢"
        return "正常"

    def _label_fluency(self, pause_count: int, hnr: Optional[float]) -> str:
        if pause_count >= 4:
            return "费力"
        if pause_count >= 2:
            return "断续"
        # HNR 很差也可能是费力
        if hnr is not None and hnr < self.HNR_SEVERE:
            return "费力"
        return "流畅"

    def _label_pause_freq(self, pause_count: int, total_seconds: float) -> str:
        if total_seconds <= 0:
            return "未测到"
        # 归一化到 5 秒基准
        normed = pause_count * (5.0 / max(total_seconds, 1.0))
        if normed >= self.PAUSE_MANY:
            return "偏多"
        return "正常"

    # ---------------------------------------------------------------- #
    # 中医辨证映射
    # ---------------------------------------------------------------- #
    def _tcm_diagnosis(self, vd: Dict[str, Any]) -> Dict[str, Any]:
        v = vd["voice"]
        r = vd["speech_rhythm"]

        zheng_set = set()
        yaodian = []

        # 音量 + 音调
        if v["volume"] in ("洪亮",) and v["pitch"] == "高亢":
            zheng_set.add("实证/热证")
            yaodian.append("声高有力")
        if v["volume"] in ("低微", "极微"):
            zheng_set.add("虚证")
            yaodian.append("声低无力")

        # 嘶哑
        if v["hoarseness"]["present"]:
            zheng_set.add("肺系失调")
            yaodian.append(f"声音嘶哑（{v['hoarseness']['degree']}）")

        # 声颤
        if v["tremor_present"]:
            zheng_set.add("气虚")
            yaodian.append("声颤")

        # 节奏
        if r["speed"] == "偏快":
            zheng_set.add("肝火/心火")
            yaodian.append("语速偏快")
        if r["speed"] == "偏慢" and r["fluency"] in ("断续", "费力"):
            zheng_set.add("气虚")
            yaodian.append("语速迟缓、说话费力")
        if r["breath_pause_frequency"] == "偏多":
            zheng_set.add("肺气虚/肾不纳气")
            yaodian.append("换气偏多")
        if r["fluency"] == "费力":
            yaodian.append("说话费力")

        if not zheng_set:
            zheng_set.add("声音平和")
            yaodian.append("语声、节奏未见明显异常")

        tiaoli = self._tiaoli_for(zheng_set)

        return {
            "主要证型": sorted(zheng_set),
            "辨证要点": yaodian,
            "调理建议": tiaoli,
        }

    @staticmethod
    def _tiaoli_for(zheng: set) -> list:
        tips = []
        if "气虚" in zheng or "肺气虚/肾不纳气" in zheng:
            tips.append("益气养肺，推荐黄芪、党参、山药，可配合八段锦调息")
        if "虚证" in zheng:
            tips.append("补益气血，忌过劳，饮食温补")
        if "实证/热证" in zheng or "肝火/心火" in zheng:
            tips.append("清热泻火，菊花、金银花泡水；情志宜舒缓")
        if "肺系失调" in zheng:
            tips.append("润肺护嗓，少辛辣，可代茶饮胖大海、麦冬")
        if not tips:
            tips.append("注意起居规律，保持心情舒畅即可")
        return tips

"""
舌诊分析模块
使用OpenCV实现真实的AI识别
"""
import cv2
import numpy as np
from sklearn.cluster import KMeans
from typing import Dict, Any, List
import json

class TongueDiagnosis:
    def __init__(self):
        """初始化舌诊分析器"""
        # 加载舌头分割模型（简化版，实际应使用训练好的模型）
        self.tongue_color_ranges = {
            'normal': {
                'lower': np.array([0, 50, 80]),  # HSV下限
                'upper': np.array([20, 200, 200])  # HSV上限
            },
            'pale': {
                'lower': np.array([0, 20, 100]),
                'upper': np.array([30, 100, 255])
            },
            'red': {
                'lower': np.array([0, 100, 100]),
                'upper': np.array([20, 255, 255])
            },
            'purple': {
                'lower': np.array([140, 50, 50]),
                'upper': np.array([180, 255, 255])
            }
        }
        
        print("✅ 舌诊分析器初始化完成")
    
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        分析舌部图片
        
        参数:
            image_bytes: 图片字节数据
        
        返回:
            舌诊结果字典
        """
        try:
            # 解码图片
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("无法解析图片")
            
            # 舌体分割
            tongue_mask = self._segment_tongue(image)
            
            if tongue_mask is None:
                raise ValueError("未能有效识别舌体")
            
            # 提取舌体区域
            tongue_roi, tongue_mask_cropped = self._extract_tongue_roi(image, tongue_mask)
            
            # 执行详细分析
            body = self._analyze_tongue_body(tongue_roi, tongue_mask_cropped)
            coating = self._analyze_tongue_coating(tongue_roi)
            sublingual_vein = self._analyze_sublingual_vein(tongue_roi)
            
            # 构建结果
            result = {
                "tongue_diagnosis": {
                    "tongue_body": body,
                    "tongue_coating": coating,
                    "sublingual_vein": sublingual_vein
                }
            }
            
            # 添加中医辨证
            result["tcm_diagnosis"] = self._get_tcm_diagnosis(result)
            
            return result
            
        except Exception as e:
            print(f"舌诊分析错误: {e}")
            raise e
    
    def _segment_tongue(self, image: np.ndarray) -> np.ndarray:
        """
        舌体分割（基于颜色和形态的方法，严格校验防止误检）
        """
        h_img, w_img = image.shape[:2]

        # 转换为HSV色彩空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 舌头核心颜色范围——收紧阈值，避免皮肤/嘴唇误判
        # 正常舌头：偏红偏粉，饱和度中等偏高，亮度适中
        lower_tongue = np.array([0, 40, 80])
        upper_tongue = np.array([18, 200, 220])

        lower_red2 = np.array([160, 40, 80])
        upper_red2 = np.array([180, 200, 220])

        mask1 = cv2.inRange(hsv, lower_tongue, upper_tongue)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        color_mask = cv2.bitwise_or(mask1, mask2)

        # 形态学操作去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)

        # 查找轮廓
        contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # 找到最大的轮廓（候选舌体）
        max_contour = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(max_contour)
        image_area = h_img * w_img

        # ===== 校验1：面积门槛提高到 8% =====
        min_area_ratio = 0.08
        if contour_area < image_area * min_area_ratio:
            print(f"[舌诊] 面积不够：{contour_area}/{image_area} = {contour_area/image_area:.3f} < {min_area_ratio}")
            return None

        # ===== 校验2：位置校验 —— 舌头应该在图片下半部分（张嘴时舌头在下颌区域）=====
        x, y, w, h = cv2.boundingRect(max_contour)
        center_y = y + h / 2
        center_x = x + w / 2

        # 舌体质心应该在图片垂直方向 40%~90% 区域（偏下）
        if center_y < h_img * 0.35 or center_y > h_img * 0.95:
            print(f"[舌诊] 位置异常：质心Y={center_y}/{h_img} = {center_y/h_img:.2f}，不在舌部预期区域")
            return None

        # ===== 校验3：宽高比校验 —— 舌体通常是横向的（宽>高）=====
        aspect_ratio = float(h) / w if w > 0 else 0
        if aspect_ratio > 1.5:
            # 太高了，不像舌头（更像脸/鼻子）
            print(f"[舌诊] 宽高比异常：{aspect_ratio:.2f}（太高），不像舌体")
            return None

        # ===== 校验4：水平居中度 —— 舌头应该在画面水平中间区域 =====
        if center_x < w_img * 0.15 or center_x > w_img * 0.85:
            print(f"[舌诊] 水平偏离过大：X={center_x}/{w_img}")
            return None

        # 创建掩码
        mask = np.zeros_like(color_mask)
        cv2.fillPoly(mask, [max_contour], 255)

        # 再次形态学处理使掩码更平滑
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)

        print(f"[舌诊] ✅ 检测通过：面积={contour_area}({contour_area/image_area:.2f}) "
              f"位置=({center_x:.0f},{center_y:.0f}) 宽高比={aspect_ratio:.2f}")

        return mask
    
    def _extract_tongue_roi(self, image: np.ndarray, mask: np.ndarray):
        """
        提取舌体感兴趣区域
        
        返回:
            (tongue_cropped, mask_cropped) 裁剪后的舌体图像和对应掩码
        """
        # 应用掩码
        tongue_roi = cv2.bitwise_and(image, image, mask=mask)
        
        # 找到边界框
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x, y, w, h = cv2.boundingRect(contours[0])
        
        # 裁剪舌体区域和掩码
        tongue_cropped = tongue_roi[y:y+h, x:x+w]
        mask_cropped = mask[y:y+h, x:x+w]
        
        return tongue_cropped, mask_cropped
    
    def _analyze_tongue_body(self, tongue_roi: np.ndarray, mask: np.ndarray) -> Dict[str, Any]:
        """
        分析舌体
        
        参数:
            tongue_roi: 舌体区域图像
            mask: 舌体掩码
        
        返回:
            舌体分析结果
        """
        # 转换为HSV色彩空间
        hsv = cv2.cvtColor(tongue_roi, cv2.COLOR_BGR2HSV)
        
        # 分析舌色
        color = self._analyze_tongue_color(hsv, mask)
        
        # 分析舌形
        shape = self._analyze_tongue_shape(mask)
        
        # 分析舌质
        texture = self._analyze_tongue_texture(tongue_roi, mask)
        
        # 舌体活动度（静态照片无法准确判断，标注为"无法判断"或默认"灵活"）
        movement = "灵活（静态图片，仅供参考）"
        
        return {
            "color": color,
            "shape": shape,
            "texture": texture,
            "movement": movement
        }
    
    def _analyze_tongue_color(self, hsv: np.ndarray, mask: np.ndarray) -> Dict[str, Any]:
        """
        分析舌色
        
        参数:
            hsv: HSV图像
            mask: 舌体掩码
        
        返回:
            舌色分析结果
        """
        # 只分析舌体区域
        tongue_pixels = hsv[mask > 0]
        
        if len(tongue_pixels) == 0:
            return {
                "main_color": "淡红",
                "uniformity": "均匀",
                "abnormal_colorations": []
            }
        
        # 使用k-means聚类找到主要颜色
        kmeans = KMeans(n_clusters=3, n_init=10, random_state=42)
        kmeans.fit(tongue_pixels)
        
        # 获取最主要的颜色
        dominant_color_hsv = kmeans.cluster_centers_[np.argmax(np.bincount(kmeans.labels_))]
        h, s, v = dominant_color_hsv
        
        # 转换H到度数
        h_deg = h * 2 if h < 128 else (h - 128) * 2
        
        # 分类舌色
        if h_deg < 10 or h_deg > 350:
            main_color = "红"
        elif 10 <= h_deg < 30:
            main_color = "淡红"
        elif 30 <= h_deg < 60:
            main_color = "黄"
        elif 60 <= h_deg < 160:
            main_color = "淡白"
        elif 160 <= h_deg < 260:
            main_color = "青紫"
        else:
            main_color = "绛"
        
        # 判断颜色均匀度
        labels = kmeans.labels_
        unique, counts = np.unique(labels, return_counts=True)
        max_proportion = np.max(counts) / len(labels)
        
        uniformity = "均匀" if max_proportion > 0.6 else "不均匀"
        
        # 检测异常着色
        abnormal_colorations = []
        if max_proportion < 0.4:
            abnormal_colorations.append("地图舌")
        
        return {
            "main_color": main_color,
            "uniformity": uniformity,
            "abnormal_colorations": abnormal_colorations
        }
    
    def _analyze_tongue_shape(self, mask: np.ndarray) -> Dict[str, Any]:
        """
        分析舌形
        
        参数:
            mask: 舌体掩码
        
        返回:
            舌形分析结果
        """
        # 计算轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {
                "size": "正常",
                "teeth_marks": "无",
                "fissures": {
                    "has_fissures": False,
                    "fissure_pattern": "",
                    "fissure_count": 0
                }
            }
        
        contour = contours[0]
        
        # 计算面积和周长
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        # 计算边界框
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(h) / w
        
        # 判断舌体大小
        if aspect_ratio > 0.7:
            size = "胖大"
        elif aspect_ratio > 0.5:
            size = "正常"
        else:
            size = "瘦薄"
        
        # 检测齿痕（通过轮廓的边缘波动）
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = float(area) / hull_area if hull_area > 0 else 1
        
        if solidity < 0.9:
            teeth_marks = "轻度"
        elif solidity < 0.85:
            teeth_marks = "中度"
        elif solidity < 0.8:
            teeth_marks = "重度齿痕"
        else:
            teeth_marks = "无"
        
        # 检测裂纹
        # 简化：使用边缘检测
        gray_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        gray = cv2.cvtColor(gray_mask, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 统计边缘线
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                                minLineLength=50, maxLineGap=10)
        
        has_fissures = lines is not None and len(lines) > 0
        
        if has_fissures:
            fissure_count = len(lines)
            # 判断裂纹类型（简化）
            if fissure_count > 10:
                fissure_pattern = "深裂纹"
            elif fissure_count > 5:
                fissure_pattern = "横裂"
            else:
                fissure_pattern = "纵裂"
        else:
            fissure_count = 0
            fissure_pattern = ""
        
        return {
            "size": size,
            "teeth_marks": teeth_marks,
            "fissures": {
                "has_fissures": has_fissures,
                "fissure_pattern": fissure_pattern,
                "fissure_count": fissure_count
            }
        }
    
    def _analyze_tongue_texture(self, tongue_roi: np.ndarray, mask: np.ndarray) -> Dict[str, Any]:
        """
        分析舌质
        
        参数:
            tongue_roi: 舌体区域图像
            mask: 舌体掩码
        
        返回:
            舌质分析结果
        """
        # 只分析舌体区域内的像素
        mask_bool = mask > 0
        tongue_pixels = tongue_roi[mask_bool]
        
        if len(tongue_pixels) == 0:
            return {
                "type": "嫩舌",
                "dryness": "正常",
                "petechiae": {
                    "has_petechiae": False,
                    "count": 0,
                    "location": [],
                    "color": ""
                }
            }
        
        # 转换为灰度
        gray = cv2.cvtColor(tongue_roi, cv2.COLOR_BGR2GRAY)
        tongue_gray = gray[mask > 0]
        
        # 计算纹理强度（老舌纹理粗糙，嫩舌纹理细腻）
        texture_variance = np.var(tongue_gray)
        
        # 判断舌质老嫩
        if texture_variance > 1000:
            type_val = "老舌"
        else:
            type_val = "嫩舌"
        
        # 分析干湿度
        hsv = cv2.cvtColor(tongue_roi, cv2.COLOR_BGR2GRAY)
        tongue_hsv = hsv[mask > 0]
        avg_brightness = np.mean(tongue_hsv)
        
        if avg_brightness > 180:
            dryness = "偏湿"
        elif avg_brightness < 120:
            dryness = "偏干"
        else:
            dryness = "正常"
        
        # 检测瘀点（检测深色斑点）
        # 简化：使用颜色阈值
        lower_dark = np.array([0, 0, 0])
        upper_dark = np.array([180, 255, 100])
        hsv_full = cv2.cvtColor(tongue_roi, cv2.COLOR_BGR2HSV)
        dark_mask = cv2.inRange(hsv_full, lower_dark, upper_dark)
        
        # 只在舌体区域内统计
        dark_in_tongue = cv2.bitwise_and(dark_mask, dark_mask, mask=mask)
        dark_count = np.count_nonzero(dark_in_tongue)
        
        has_petechiae = dark_count > 100
        
        if has_petechiae:
            # 统计瘀点数量
            contours, _ = cv2.findContours(dark_in_tongue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            petechiae_contours = [c for c in contours if cv2.contourArea(c) > 5]
            petechiae_count = len(petechiae_contours)
            
            # 判断瘀点颜色——基于暗色区域的实际HSV值
            dark_pixels_hsv = hsv_full[dark_in_tongue > 0]
            if len(dark_pixels_hsv) > 0:
                avg_v = np.mean(dark_pixels_hsv[:, 2])
                avg_s = np.mean(dark_pixels_hsv[:, 1])
                if avg_v < 50:
                    petechiae_color = "紫黑"
                elif avg_v < 80:
                    petechiae_color = "紫暗"
                else:
                    petechiae_color = "淡紫"
            else:
                petechiae_color = "淡紫"
            
            # 瘀点位置——基于轮廓质心在舌体中的实际位置
            tongue_h, tongue_w = tongue_roi.shape[:2]
            location = set()
            for c in petechiae_contours[:20]:  # 最多分析20个
                M = cv2.moments(c)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    # 根据位置分类
                    rel_x = cx / tongue_w
                    rel_y = cy / tongue_h
                    if rel_y < 0.3:
                        location.add("舌尖")
                    elif rel_y > 0.7:
                        location.add("舌根")
                    elif rel_x < 0.3 or rel_x > 0.7:
                        location.add("舌边")
                    else:
                        location.add("舌中")
            location = list(location) if location else ["舌中"]
        else:
            petechiae_count = 0
            petechiae_color = ""
            location = []
        
        return {
            "type": type_val,
            "dryness": dryness,
            "petechiae": {
                "has_petechiae": has_petechiae,
                "count": petechiae_count,
                "location": location,
                "color": petechiae_color
            }
        }
    
    def _analyze_tongue_coating(self, tongue_roi: np.ndarray) -> Dict[str, Any]:
        """
        分析舌苔
        
        参数:
            tongue_roi: 舌体区域图像
        
        返回:
            舌苔分析结果
        """
        # 转换为HSV色彩空间
        hsv = cv2.cvtColor(tongue_roi, cv2.COLOR_BGR2HSV)
        
        # 分析苔色
        color = self._analyze_coating_color(hsv)
        
        # 分析苔厚薄
        thickness = self._analyze_coating_thickness(hsv)
        
        # 分析分布
        distribution = self._analyze_coating_distribution(hsv)
        
        # 分析苔质
        texture = self._analyze_coating_texture(hsv)
        
        return {
            "color": color,
            "thickness": thickness,
            "distribution": distribution,
            "texture": texture
        }
    
    def _analyze_coating_color(self, hsv: np.ndarray) -> Dict[str, str]:
        """分析苔色"""
        # 获取所有像素
        pixels = hsv.reshape(-1, 3)
        
        # 使用k-means聚类
        kmeans = KMeans(n_clusters=2, n_init=10, random_state=42)
        kmeans.fit(pixels)
        
        # 获取主要颜色
        dominant_color_hsv = kmeans.cluster_centers_[np.argmax(np.bincount(kmeans.labels_))]
        h, s, v = dominant_color_hsv
        
        # 转换H到度数
        h_deg = h * 2 if h < 128 else (h - 128) * 2
        
        # 分类苔色
        if s < 50:  # 低饱和度
            main_color = "白苔"
        elif h_deg < 60:  # 黄色范围
            main_color = "黄苔"
        elif h_deg < 120:  # 绿色/灰色范围
            main_color = "灰黑苔"
        else:
            main_color = "霉酱色苔"
        
        # 判断均匀度
        labels = kmeans.labels_
        unique, counts = np.unique(labels, return_counts=True)
        max_proportion = np.max(counts) / len(labels)
        
        uniformity = "均匀" if max_proportion > 0.7 else "不均匀"
        
        return {
            "main_color": main_color,
            "uniformity": uniformity
        }
    
    def _analyze_coating_thickness(self, hsv: np.ndarray) -> Dict[str, Any]:
        """分析苔厚薄"""
        # 通过颜色覆盖率和饱和度判断厚度
        # 厚苔颜色更鲜艳，覆盖更均匀
        
        # 计算平均饱和度
        avg_saturation = np.mean(hsv[:, :, 1])
        
        # 判断厚度
        if avg_saturation < 50:
            level = "薄苔"
            thickness_value = (avg_saturation / 50) * 5
        elif avg_saturation < 120:
            level = "厚苔"
            thickness_value = 5 + (avg_saturation - 50) / 70 * 3
        else:
            level = "腻苔"
            thickness_value = 8 + (avg_saturation - 120) / 135 * 2
        
        return {
            "level": level,
            "thickness_value": f"{thickness_value:.1f}"
        }
    
    def _analyze_coating_distribution(self, hsv: np.ndarray) -> Dict[str, Any]:
        """分析舌苔分布"""
        # 将舌体分为几个区域
        h, w = hsv.shape[:2]
        
        # 前部、中部、后部
        front_region = hsv[:int(h*0.3), :]
        middle_region = hsv[int(h*0.3):int(h*0.7), :]
        back_region = hsv[int(h*0.7):, :]
        
        # 计算各区域的平均饱和度
        front_sat = np.mean(front_region[:, :, 1])
        middle_sat = np.mean(middle_region[:, :, 1])
        back_sat = np.mean(back_region[:, :, 1])
        
        # 判断分布模式
        if back_sat > middle_sat > front_sat:
            distribution_pattern = "前薄后厚"
        elif front_sat > middle_sat > back_sat:
            distribution_pattern = "前厚后薄"
        elif abs(front_sat - back_sat) < 10 and middle_sat < front_sat - 10:
            distribution_pattern = "两侧偏厚"
        elif middle_sat > front_sat and middle_sat > back_sat:
            distribution_pattern = "中部偏厚"
        else:
            distribution_pattern = "均匀分布"
        
        # 判断是否全覆盖
        avg_saturation = np.mean(hsv[:, :, 1])
        coverage = "全覆盖" if avg_saturation > 30 else "局部覆盖"
        
        # 判断是否地图舌（简化：检查颜色分布的不均匀性）
        sat_variance = np.var(hsv[:, :, 1])
        mapping_tongue = sat_variance > 1000
        
        return {
            "coverage": coverage,
            "distribution_pattern": distribution_pattern,
            "mapping_tongue": mapping_tongue
        }
    
    def _analyze_coating_texture(self, hsv: np.ndarray) -> Dict[str, str]:
        """分析苔质"""
        # 转换为灰度
        gray = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
        
        # 计算纹理强度
        texture_variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 计算腻感（通过边缘密度）
        edges = cv2.Canny(gray, 30, 100)
        edge_density = np.mean(edges > 0)
        
        # 判断苔质类型
        if texture_variance > 500 and edge_density < 0.02:
            type_val = "腻苔"
        elif texture_variance > 800:
            type_val = "糙苔"
        elif texture_variance < 100:
            type_val = "剥脱"
        else:
            type_val = "正常"
        
        # 判断腻感程度
        if edge_density < 0.01:
            greasiness = "重度腻"
        elif edge_density < 0.02:
            greasiness = "中度腻"
        elif edge_density < 0.05:
            greasiness = "轻度腻"
        else:
            greasiness = "无"
        
        return {
            "type": type_val,
            "greasiness": greasiness
        }
    
    def _analyze_sublingual_vein(self, tongue_roi: np.ndarray) -> Dict[str, Any]:
        """
        分析舌下络脉
        
        参数:
            tongue_roi: 舌体区域图像
        
        返回:
            舌下络脉分析结果
        """
        # 转换为HSV
        hsv = cv2.cvtColor(tongue_roi, cv2.COLOR_BGR2HSV)
        
        # 检测紫色/暗色区域（络脉）
        lower_purple = np.array([140, 50, 50])
        upper_purple = np.array([180, 255, 255])
        
        vein_mask = cv2.inRange(hsv, lower_purple, upper_purple)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        vein_mask = cv2.morphologyEx(vein_mask, cv2.MORPH_CLOSE, kernel)
        vein_mask = cv2.morphologyEx(vein_mask, cv2.MORPH_OPEN, kernel)
        
        # 查找络脉轮廓
        contours, _ = cv2.findContours(vein_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        visible = len(contours) > 0
        
        if not visible:
            return {
                "visible": False,
                "color": "",
                "width": {"status": "", "width_value": ""},
                "tortuosity": "",
                "length": "",
                "branching": {"has_branching": False, "branch_count": 0},
                "stasis": {"has_stasis": False, "stasis_degree": ""}
            }
        
        # 获取最大的络脉
        main_vein = max(contours, key=cv2.contourArea)
        
        # 计算络脉特征
        area = cv2.contourArea(main_vein)
        perimeter = cv2.arcLength(main_vein, True)
        
        # 边界框
        x, y, w, h = cv2.boundingRect(main_vein)
        
        # 判断颜色
        vein_pixels = hsv[vein_mask > 0]
        if len(vein_pixels) > 0:
            avg_h = np.mean(vein_pixels[:, 0])
            avg_s = np.mean(vein_pixels[:, 1])
            
            if avg_s < 100:
                color = "淡紫"
            elif avg_h < 150:
                color = "青紫"
            elif avg_h < 165:
                color = "紫暗"
            else:
                color = "紫黑"
        else:
            color = "紫暗"
        
        # 判断粗细
        width_value = f"{w:.2f}"
        if w < 3:
            width_status = "正常"
        elif w < 5:
            width_status = "增粗"
        else:
            width_status = "明显增粗"
        
        # 判断迂曲程度（通过轮廓的复杂度）
        hull = cv2.convexHull(main_vein)
        hull_area = cv2.contourArea(hull)
        solidity = float(area) / hull_area if hull_area > 0 else 1
        
        if solidity > 0.9:
            tortuosity = "正常"
        elif solidity > 0.8:
            tortuosity = "轻度迂曲"
        elif solidity > 0.7:
            tortuosity = "中度迂曲"
        else:
            tortuosity = "明显迂曲"
        
        # 计算长度
        length = f"{h:.1f}"
        
        # 检测分支
        branch_count = len([c for c in contours if cv2.contourArea(c) > 50])
        has_branching = branch_count > 1
        
        # 判断瘀血（基于颜色和形态）
        has_stasis = color in ["紫暗", "紫黑"] and tortuosity != "正常"
        stasis_degree = "轻度" if has_stasis else ""
        if has_stasis and tortuosity == "明显迂曲":
            stasis_degree = "重度"
        elif has_stasis and tortuosity in ["中度迂曲", "明显迂曲"]:
            stasis_degree = "中度"
        
        return {
            "visible": True,
            "color": color,
            "width": {
                "status": width_status,
                "width_value": width_value
            },
            "tortuosity": tortuosity,
            "length": length,
            "branching": {
                "has_branching": has_branching,
                "branch_count": branch_count
            },
            "stasis": {
                "has_stasis": has_stasis,
                "stasis_degree": stasis_degree
            }
        }
    
    def _get_tcm_diagnosis(self, result: Dict) -> Dict[str, Any]:
        """
        根据舌诊结果进行中医辨证
        
        参数:
            result: 舌诊结果
        
        返回:
            中医辨证结果
        """
        diagnosis = {
            "主要证型": [],
            "辨证要点": [],
            "调理建议": []
        }
        
        tongue_body = result["tongue_diagnosis"]["tongue_body"]
        tongue_coating = result["tongue_diagnosis"]["tongue_coating"]
        
        # 根据舌色辨证
        tongue_color = tongue_body["color"]["main_color"]
        color_diagnosis = {
            "淡白": ("气血两虚", "补气养血", ["当归", "黄芪", "红枣"]),
            "淡红": ("气血调和", "保持现状", ["山药", "茯苓"]),
            "红": ("热证", "清热", ["生石膏", "知母", "黄连"]),
            "绛": ("热入营血", "清热凉血", ["玄参", "生地", "丹皮"]),
            "青紫": ("血瘀", "活血化瘀", ["丹参", "桃仁", "红花"])
        }
        
        if tongue_color in color_diagnosis:
            zheng_type, treatment, herbs = color_diagnosis[tongue_color]
            diagnosis["主要证型"].append(zheng_type)
            diagnosis["辨证要点"].append(f"舌色{tongue_color}")
            diagnosis["调理建议"].append(f"{treatment}，如{'、'.join(herbs)}")
        
        # 根据舌苔辨证
        coating_color = tongue_coating["color"]["main_color"]
        coating_thickness = tongue_coating["thickness"]["level"]
        
        if coating_color == "白苔":
            diagnosis["辨证要点"].append("舌苔白色")
            if coating_thickness == "厚苔" or coating_thickness == "腻苔":
                diagnosis["主要证型"].append("寒湿")
                diagnosis["调理建议"].append("散寒化湿，如苍术、厚朴")
        
        elif coating_color == "黄苔":
            diagnosis["主要证型"].append("热证")
            diagnosis["辨证要点"].append("舌苔黄色")
            if coating_thickness == "厚苔" or coating_thickness == "腻苔":
                diagnosis["主要证型"].append("湿热")
                diagnosis["调理建议"].append("清热利湿，如黄连、黄芩、茯苓")
            else:
                diagnosis["调理建议"].append("清热泻火，如黄连、栀子")
        
        elif coating_color == "灰黑苔":
            diagnosis["主要证型"].append("里寒或里热重症")
            diagnosis["调理建议"].append("根据其他症状辨证施治")
        
        # 根据舌形辨证
        tongue_size = tongue_body["shape"]["size"]
        teeth_marks = tongue_body["shape"]["teeth_marks"]
        fissures = tongue_body["shape"]["fissures"]
        
        if tongue_size == "胖大":
            diagnosis["主要证型"].append("脾虚湿盛")
            diagnosis["调理建议"].append("健脾利湿，如白术、茯苓、山药")
        elif tongue_size == "瘦薄":
            diagnosis["主要证型"].append("阴虚")
            diagnosis["调理建议"].append("滋阴降火，如麦冬、沙参、枸杞")
        
        if teeth_marks != "无":
            diagnosis["主要证型"].append("脾虚湿盛")
            diagnosis["辨证要点"].append("舌体有齿痕")
        
        if fissures["has_fissures"]:
            diagnosis["主要证型"].append("阴虚")
            diagnosis["辨证要点"].append("舌体有裂纹")
        
        # 根据舌质辨证
        texture_type = tongue_body["texture"]["type"]
        dryness = tongue_body["texture"]["dryness"]
        petechiae = tongue_body["texture"]["petechiae"]
        
        if texture_type == "老舌":
            diagnosis["辨证要点"].append("舌质老")
        elif texture_type == "嫩舌":
            diagnosis["辨证要点"].append("舌质嫩")
        
        if dryness == "偏干":
            diagnosis["主要证型"].append("阴虚津亏")
            diagnosis["调理建议"].append("滋阴生津，如麦冬、玉竹")
        elif dryness == "偏湿":
            diagnosis["主要证型"].append("湿盛")
            diagnosis["调理建议"].append("利湿化浊，如茯苓、薏仁")
        
        if petechiae["has_petechiae"]:
            diagnosis["主要证型"].append("血瘀")
            diagnosis["辨证要点"].append("舌有瘀点")
            diagnosis["调理建议"].append("活血化瘀，如丹参、赤芍")
        
        # 根据舌下络脉辨证
        sublingual_vein = result["tongue_diagnosis"]["sublingual_vein"]
        if sublingual_vein["visible"]:
            vein_color = sublingual_vein["color"]
            vein_stasis = sublingual_vein["stasis"]["has_stasis"]
            
            if vein_stasis:
                diagnosis["主要证型"].append("血瘀")
                diagnosis["辨证要点"].append(f"舌下络脉{sublingual_vein['width']['status']}")
                diagnosis["调理建议"].append("活血化瘀通络")
            
            if vein_color == "青紫":
                diagnosis["辨证要点"].append("舌下络脉青紫")
        
        # 去重
        diagnosis["主要证型"] = list(set(diagnosis["主要证型"]))
        
        return diagnosis

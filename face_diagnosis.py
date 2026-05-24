"""
面诊分析模块
使用OpenCV和MediaPipe实现真实的AI识别
"""
import cv2
import numpy as np
import mediapipe as mp
from sklearn.cluster import KMeans
import json
from typing import Dict, Any
from io import BytesIO

class FaceDiagnosis:
    def __init__(self):
        """初始化面诊分析器"""
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.5
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        print("✅ 面诊分析器初始化完成")
    
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        分析面部图片
        
        参数:
            image_bytes: 图片字节数据
        
        返回:
            面诊结果字典
        """
        try:
            # 解码图片
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("无法解析图片")
            
            # 转换为RGB格式（MediaPipe需要）
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 人脸检测
            results = self.face_detection.process(image_rgb)
            
            if results.detections is None or len(results.detections) == 0:
                raise ValueError("未检测到人脸")
            
            # 获取人脸检测结果
            detection = results.detections[0]
            bbox = self._get_bbox(image, detection)
            
            # 裁剪人脸区域
            face_roi = image[bbox['y']:bbox['y']+bbox['h'], 
                            bbox['x']:bbox['x']+bbox['w']]
            
            # 执行详细分析
            complexion = self._analyze_complexion(face_roi)
            spirit = self._analyze_spirit(image, detection)
            features = self._analyze_features(face_roi)
            
            # 构建结果
            result = {
                "facial_diagnosis": {
                    "complexion_color": complexion,
                    "spirit_expression": spirit,
                    "facial_features": features
                }
            }
            
            # 添加中医辨证
            result["tcm_diagnosis"] = self._get_tcm_diagnosis(result)
            
            return result
            
        except Exception as e:
            print(f"面诊分析错误: {e}")
            raise e
    
    def _get_bbox(self, image: np.ndarray, detection) -> Dict[str, int]:
        """获取人脸边界框"""
        h, w = image.shape[:2]
        bbox = detection.location_data.relative_bounding_box
        
        x = int(bbox.xmin * w)
        y = int(bbox.ymin * h)
        width = int(bbox.width * w)
        height = int(bbox.height * h)
        
        # 边界检查
        x = max(0, x)
        y = max(0, y)
        width = min(width, w - x)
        height = min(height, h - y)
        
        return {'x': x, 'y': y, 'w': width, 'h': height}
    
    def _analyze_complexion(self, face_roi: np.ndarray) -> Dict[str, Any]:
        """
        分析面色
        
        参数:
            face_roi: 人脸区域图像
        
        返回:
            面色分析结果
        """
        # 转换为HSV色彩空间
        hsv = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
        
        # 提取主要颜色（使用k-means聚类）
        pixels = hsv.reshape(-1, 3)
        kmeans = KMeans(n_clusters=3, n_init=10, random_state=42)
        kmeans.fit(pixels)
        
        # 获取最主要的颜色
        dominant_color_hsv = kmeans.cluster_centers_[np.argmax(kmeans.labels_ == kmeans.labels_[0])]
        
        # 判断主色调
        primary_color = self._classify_skin_color(dominant_color_hsv)
        
        # 分析颜色分布
        color_distribution = self._analyze_color_distribution(kmeans.labels_)
        
        # 分析光泽度
        brightness = self._analyze_brightness(face_roi)
        
        # 分析光泽感
        glossiness = self._analyze_glossiness(face_roi)
        
        return {
            "primary_color": primary_color,
            "color_distribution": color_distribution,
            "brightness": brightness,
            "glossiness": glossiness
        }
    
    def _classify_skin_color(self, hsv_color: np.ndarray) -> str:
        """
        根据HSV值分类肤色
        
        参数:
            hsv_color: HSV颜色值
        
        返回:
            肤色类别
        """
        h, s, v = hsv_color
        
        # 转换H到度数（0-360）
        h_deg = h * 2
        
        # 根据H值判断色调
        if h_deg < 10 or h_deg > 350:
            return "红"
        elif 10 <= h_deg < 30:
            return "淡红"
        elif 30 <= h_deg < 60:
            return "黄"
        elif 60 <= h_deg < 160:
            return "淡白"
        elif 160 <= h_deg < 260:
            return "青"
        else:
            return "黑"
    
    def _analyze_color_distribution(self, labels: np.ndarray) -> str:
        """分析颜色分布"""
        # 计算各类别的比例
        unique, counts = np.unique(labels, return_counts=True)
        proportions = counts / len(labels)
        
        # 如果最大类别的占比超过70%，则为均匀
        if np.max(proportions) > 0.7:
            return "均匀"
        else:
            return "斑块状"
    
    def _analyze_brightness(self, face_roi: np.ndarray) -> int:
        """
        分析亮度（光泽度）
        
        返回:
            0-100的亮度评分
        """
        # 转换为灰度图
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 计算平均亮度
        avg_brightness = np.mean(gray)
        
        # 归一化到0-100
        brightness_score = int(np.clip(avg_brightness / 255 * 100, 0, 100))
        
        return brightness_score
    
    def _analyze_glossiness(self, face_roi: np.ndarray) -> str:
        """
        分析光泽感
        
        返回:
            光泽感描述
        """
        # 计算边缘强度（光泽越多，边缘越清晰）
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.mean(edges > 0)
        
        if edge_density > 0.15:
            return "有光泽"
        elif edge_density > 0.08:
            return "无光泽"
        else:
            return "晦暗"
    
    def _analyze_spirit(self, image: np.ndarray, detection) -> Dict[str, Any]:
        """
        分析神态
        """
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mesh_results = self.face_mesh.process(image_rgb)
        
        if mesh_results.multi_face_landmarks:
            landmarks = mesh_results.multi_face_landmarks[0]
            eye_condition = self._analyze_eyes(image, landmarks)
            facial_expression = self._analyze_expression(landmarks)
        else:
            eye_condition = {
                "brightness": "明亮",
                "dark_circles": "无",
                "eye_bags": "无",
                "redness": "无"
            }
            facial_expression = "自然"
        
        mental_state = self._determine_mental_state(eye_condition, facial_expression)
        
        return {
            "mental_state": mental_state,
            "eye_condition": eye_condition,
            "facial_expression": facial_expression
        }
    
    def _analyze_eyes(self, image: np.ndarray, landmarks) -> Dict[str, str]:
        """分析眼睛状况 —— 基于真实图像像素"""
        h, w = image.shape[:2]

        # 获取眼睛关键点
        left_eye = self._get_eye_landmarks(landmarks, 'left')
        right_eye = self._get_eye_landmarks(landmarks, 'right')
        
        # 眼睛睁开程度
        left_eye_open = abs(left_eye['top'][1] - left_eye['bottom'][1])
        right_eye_open = abs(right_eye['top'][1] - right_eye['bottom'][1])
        avg_open = (left_eye_open + right_eye_open) / 2
        
        if avg_open > 0.02:
            brightness = "明亮"
        elif avg_open > 0.015:
            brightness = "暗淡"
        else:
            brightness = "呆滞"

        # --- 黑眼圈：分析眼睛下方区域的亮度 ---
        # 左眼下方关键点 130(外), 133(内)
        le_outer = landmarks.landmark[130]
        le_inner = landmarks.landmark[133]
        re_outer = landmarks.landmark[359]
        re_inner = landmarks.landmark[362]

        under_eye_regions = []
        for outer, inner in [(le_outer, le_inner), (re_outer, re_inner)]:
            x1 = int(min(outer.x, inner.x) * w)
            x2 = int(max(outer.x, inner.x) * w)
            y1 = int(max(outer.y, inner.y) * h)
            y2 = int(y1 + (x2 - x1) * 0.35)  # 取眼下一小条
            x1, x2 = max(0, x1), min(w, x2)
            y1, y2 = max(0, y1), min(h, y2)
            if x2 > x1 and y2 > y1:
                under_eye_regions.append(image[y1:y2, x1:x2])

        if under_eye_regions:
            avg_under_eye_v = np.mean([np.mean(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)) for r in under_eye_regions])
            # 低亮度 → 黑眼圈
            if avg_under_eye_v < 90:
                dark_circles = "重度"
            elif avg_under_eye_v < 120:
                dark_circles = "中度"
            elif avg_under_eye_v < 150:
                dark_circles = "轻度"
            else:
                dark_circles = "无"
        else:
            dark_circles = "无"

        # --- 眼袋：检测眼下区域的纹理复杂度（浮肿 → 边缘模糊） ---
        if under_eye_regions:
            edge_densities = []
            for r in under_eye_regions:
                gray_r = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray_r, 30, 100)
                edge_densities.append(np.mean(edges > 0))
            avg_edge = np.mean(edge_densities)
            if avg_edge < 0.02:
                eye_bags = "重度"
            elif avg_edge < 0.05:
                eye_bags = "中度"
            elif avg_edge < 0.08:
                eye_bags = "轻度"
            else:
                eye_bags = "无"
        else:
            eye_bags = "无"

        # --- 眼白充血：分析眼白区域红色通道占比 ---
        # 简化：取眼角之间区域的 R/G 比
        redness = "无"
        try:
            for outer, inner in [(le_outer, le_inner), (re_outer, re_inner)]:
                ex1 = int(min(outer.x, inner.x) * w)
                ex2 = int(max(outer.x, inner.x) * w)
                ey1 = int(min(outer.y, inner.y) * h)
                ey2 = int(max(outer.y, inner.y) * h)
                ex1, ex2 = max(0, ex1), min(w, ex2)
                ey1, ey2 = max(0, ey1), min(h, ey2)
                if ex2 > ex1 and ey2 > ey1:
                    eye_roi = image[ey1:ey2, ex1:ex2]
                    b, g, r = cv2.split(eye_roi)
                    r_mean = np.mean(r.astype(float))
                    g_mean = np.mean(g.astype(float))
                    if g_mean > 0:
                        rg_ratio = r_mean / g_mean
                        if rg_ratio > 1.5:
                            redness = "充血"
                            break
                        elif rg_ratio > 1.2:
                            redness = "眼白有红血丝"
        except Exception:
            pass

        return {
            "brightness": brightness,
            "dark_circles": dark_circles,
            "eye_bags": eye_bags,
            "redness": redness
        }
    
    def _get_eye_landmarks(self, landmarks, eye_side):
        """获取眼睛关键点"""
        # MediaFaceMesh的眼睛关键点索引
        if eye_side == 'left':
            top_idx = 159
            bottom_idx = 145
        else:
            top_idx = 386
            bottom_idx = 374
        
        return {
            'top': [landmarks.landmark[top_idx].x, landmarks.landmark[top_idx].y],
            'bottom': [landmarks.landmark[bottom_idx].x, landmarks.landmark[bottom_idx].y]
        }
    
    def _analyze_expression(self, landmarks) -> str:
        """分析面部表情"""
        # 嘴角角度（简化判断）
        left_mouth = landmarks.landmark[61]
        right_mouth = landmarks.landmark[291]
        
        mouth_width = abs(left_mouth.x - right_mouth.x)
        
        # 简化的表情判断
        if mouth_width > 0.15:
            return "焦虑"
        else:
            return "自然"
    
    def _determine_mental_state(self, eye_condition: Dict, expression: str) -> str:
        """判断精神状态"""
        if eye_condition['brightness'] == "呆滞":
            return "萎靡不振"
        elif eye_condition['brightness'] == "暗淡":
            return "疲惫"
        else:
            return "精神饱满"
    
    def _analyze_features(self, face_roi: np.ndarray) -> Dict[str, Any]:
        """
        分析面部特征
        
        参数:
            face_roi: 人脸区域图像
        
        返回:
            面部特征分析结果
        """
        # 分析发质（基于头发区域的纹理和颜色）
        hair_condition = self._analyze_hair_condition(face_roi)
        
        # 分析浮肿
        facial_puffiness = self._analyze_facial_puffiness(face_roi)
        
        # 分析皮肤纹理
        skin_texture = self._analyze_skin_texture(face_roi)
        
        return {
            "hair_condition": hair_condition,
            "facial_puffiness": facial_puffiness,
            "skin_texture": skin_texture
        }
    
    def _analyze_hair_condition(self, face_roi: np.ndarray) -> Dict[str, str]:
        """分析发质"""
        # 计算头发区域的纹理
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 获取上半部分（头发区域）
        hair_region = gray[:int(face_roi.shape[0] * 0.3), :]
        
        # 计算纹理强度
        laplacian_var = cv2.Laplacian(hair_region, cv2.CV_64F).var()
        
        # 判断光泽
        if laplacian_var > 200:
            shine = "光泽"
        elif laplacian_var > 100:
            shine = "干燥"
        else:
            shine = "毛躁"
        
        # 密度判断：根据头发区域的暗色像素占比
        hair_hsv = cv2.cvtColor(face_roi[:int(face_roi.shape[0] * 0.3), :], cv2.COLOR_BGR2HSV)
        dark_pixels = np.sum(hair_hsv[:, :, 2] < 80)
        total_pixels = hair_hsv.shape[0] * hair_hsv.shape[1]
        dark_ratio = dark_pixels / total_pixels if total_pixels > 0 else 0

        if dark_ratio > 0.6:
            density = "浓密"
        elif dark_ratio > 0.35:
            density = "正常"
        elif dark_ratio > 0.15:
            density = "稀疏"
        else:
            density = "明显脱发"
        
        return {
            "shine": shine,
            "density": density
        }
    
    def _analyze_facial_puffiness(self, face_roi: np.ndarray) -> Dict[str, str]:
        """分析浮肿"""
        # 获取下半部分（易浮肿区域）
        lower_face = face_roi[int(face_roi.shape[0] * 0.6):, :]
        
        # 计算边缘密度（浮肿时边缘模糊）
        gray = cv2.cvtColor(lower_face, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.mean(edges > 0)
        
        # 判断浮肿程度
        if edge_density > 0.1:
            status = "无"
        elif edge_density > 0.06:
            status = "轻度"
        elif edge_density > 0.03:
            status = "中度"
        else:
            status = "重度浮肿"
        
        # 浮肿位置：基于上下区域亮度差异判断
        upper_face = face_roi[:int(face_roi.shape[0] * 0.4), :]
        upper_gray = cv2.cvtColor(upper_face, cv2.COLOR_BGR2GRAY)
        upper_brightness = np.mean(upper_gray)
        lower_brightness = np.mean(gray)

        if upper_brightness > lower_brightness + 15:
            location = "下颌"
        elif upper_brightness < lower_brightness - 10:
            location = "眼周"
        else:
            location = "全脸"
        
        return {
            "status": status,
            "location": location
        }
    
    def _analyze_skin_texture(self, face_roi: np.ndarray) -> Dict[str, str]:
        """分析皮肤纹理"""
        # 转换为灰度图
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 计算皮肤纹理强度
        texture_variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 判断出油
        if texture_variance > 150:
            oiliness = "油腻"
        elif texture_variance > 80:
            oiliness = "正常"
        else:
            oiliness = "干燥"
        
        # 判断毛孔
        if texture_variance > 120:
            pores = "粗大"
        elif texture_variance > 60:
            pores = "正常"
        else:
            pores = "细腻"
        
        # 判断弹性（基于边缘清晰度）
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size
        
        if edge_ratio > 0.05:
            elasticity = "紧致"
        elif edge_ratio > 0.03:
            elasticity = "正常"
        else:
            elasticity = "松弛"
        
        return {
            "oiliness": oiliness,
            "pores": pores,
            "elasticity": elasticity
        }
    
    def _get_tcm_diagnosis(self, result: Dict) -> Dict[str, Any]:
        """
        根据面诊结果进行中医辨证
        
        参数:
            result: 面诊结果
        
        返回:
            中医辨证结果
        """
        diagnosis = {
            "主要证型": [],
            "辨证要点": [],
            "调理建议": []
        }
        
        complexion = result["facial_diagnosis"]["complexion_color"]["primary_color"]
        mental_state = result["facial_diagnosis"]["spirit_expression"]["mental_state"]
        
        # 根据面色辨证
        complexion_diagnosis = {
            "淡白": ("气血两虚", "补气养血", ["当归", "黄芪", "红枣"]),
            "淡红": ("气血平和", "保持现状", ["山药", "茯苓"]),
            "红": ("热证", "清热泻火", ["金银花", "菊花", "绿豆"]),
            "黄": ("湿热", "清热利湿", ["黄连", "茯苓", "薏仁"]),
            "青": ("寒凝血瘀", "温经散寒", ["生姜", "红花"]),
            "黑": ("肾虚", "补肾填精", ["枸杞", "黑芝麻", "杜仲"])
        }
        
        if complexion in complexion_diagnosis:
            zheng_type, treatment, herbs = complexion_diagnosis[complexion]
            diagnosis["主要证型"].append(zheng_type)
            diagnosis["辨证要点"].append(f"面色{complexion}")
            diagnosis["调理建议"].append(f"{treatment}，如{'、'.join(herbs)}")
        
        # 根据神态辨证
        if mental_state == "萎靡不振":
            diagnosis["主要证型"].append("阳虚")
            diagnosis["调理建议"].append("温阳益气，如附子、肉桂")
        elif mental_state == "疲惫":
            diagnosis["主要证型"].append("气虚")
            diagnosis["调理建议"].append("补气健脾，如人参、白术")
        
        # 去重
        diagnosis["主要证型"] = list(set(diagnosis["主要证型"]))
        
        return diagnosis

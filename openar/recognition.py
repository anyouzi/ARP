"""
图像识别模块 — 模板匹配

对应 C++ 的 ImageRecognition/ 系列文件

方法:
    cv2.matchTemplate() + TM_CCOEFF_NORMED
    这是 OpenCV 内置的归一化相关系数匹配, 和原项目的 PSR/MPR 效果类似,
    但没有 CUDA 也能跑 (CPU 够快).

数据结构:
    Point: 匹配结果点, 含 is_empty 标志 (与原项目一致)
"""

from dataclasses import dataclass
from typing import Optional
import cv2
import numpy as np


@dataclass
class Point:
    """
    匹配结果点 — 对应 C++ 的 struct ar::point

    is_empty = True 表示没有匹配到任何目标
    """
    x: int = 0
    y: int = 0
    is_empty: bool = True

    def __bool__(self):
        """方便用 if point: 判断是否匹配成功"""
        return not self.is_empty


class TemplateMatcher:
    """
    模板匹配器

    使用方法:
        matcher = TemplateMatcher()
        screen = controller.screencap()          # 截屏
        result = matcher.find(screen, "res/login_btn.png", threshold=0.95)
        if result:
            controller.click(result.x, result.y)
    """

    def __init__(self):
        """初始化 (无状态, 预留给未来可能的 GPU 加速)"""
        self._cache = {}  # 内存缓存已加载的模板图, 避免反复读磁盘

    def find(self, image: np.ndarray, template_path: str,
             threshold: float = 0.95) -> Point:
        """
        在大图 image 中寻找模板 template_path 的位置

        参数:
            image:         截屏图像 (BGR numpy array)
            template_path: 模板图片文件路径 (如 "res/login_btn.png")
            threshold:     匹配阈值, 0.0~1.0, 默认 0.95

        返回:
            Point 对象 — 找到则 is_empty=False, 含中心坐标
                         未找到则 is_empty=True
        """
        # 加载模板图 (带缓存)
        template = self._load_template(template_path)
        if template is None:
            return Point(is_empty=True)

        # 检查模板是否比截图大
        if (template.shape[0] > image.shape[0] or
                template.shape[1] > image.shape[1]):
            return Point(is_empty=True)

        # ── 核心: 模板匹配 ──
        # TM_CCOEFF_NORMED: 归一化相关系数, 值域 [-1, 1], 1=完美匹配
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)

        # 找最大值位置
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            # 计算模板中心坐标
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return Point(x=center_x, y=center_y, is_empty=False)

        return Point(is_empty=True)

    def find_multi(self, image: np.ndarray, template_path: str,
                   threshold: float = 0.95) -> list:
        """
        多目标匹配 — 找出所有超过阈值的匹配位置

        用于屏幕上同时出现多个相同按钮的场景

        返回: Point 列表 (可能为空)
        """
        template = self._load_template(template_path)
        if template is None:
            return []

        if (template.shape[0] > image.shape[0] or
                template.shape[1] > image.shape[1]):
            return []

        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        h, w = template.shape[:2]

        # 找出所有超过阈值的位置
        locations = np.where(result >= threshold)
        points = []
        for pt in zip(*locations[::-1]):  # (x, y) 格式
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            points.append(Point(x=center_x, y=center_y, is_empty=False))

        return points

    def _load_template(self, path: str) -> Optional[np.ndarray]:
        """加载模板图片 (带缓存)"""
        if path in self._cache:
            return self._cache[path]
        img = cv2.imread(path)
        if img is None:
            from .logger import log_error
            log_error(f"无法加载模板图: {path}")
            return None
        self._cache[path] = img
        return img

    def clear_cache(self):
        """清空模板缓存"""
        self._cache.clear()


# ── 便捷函数 ────────────────────────────────────────────

def compare_image(controller, template_path: str,
                  threshold: float = 0.95) -> Point:
    """
    便捷函数: 截屏 + 模板匹配一步完成

    用法:
        result = compare_image(ctrl, "res/button.png", 0.95)
        if result:
            ctrl.click(result.x, result.y)
    """
    matcher = TemplateMatcher()
    screen = controller.screencap()
    if screen is None:
        return Point(is_empty=True)
    return matcher.find(screen, template_path, threshold)

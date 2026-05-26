"""
桌面控制器 — 替代 ADB 控制器, 直接控制 Windows 桌面

通过 mss 截屏 + pyautogui 控制鼠标键盘.

支持:
  - 全屏模式 (window_title = None): 操作整个桌面, 坐标 = 屏幕绝对坐标
  - 窗口模式 (window_title = "微信"): 只截取并操作指定窗口, 坐标相对窗口左上角

依赖:
    pip install mss pyautogui pygetwindow

使用示例:
    # 全屏模式
    ctrl = DesktopController()

    # 窗口模式
    ctrl = DesktopController(window_title="记事本")

    ctrl.connect()
    frame = ctrl.screencap()
    ctrl.click(500, 300)
    ctrl.disconnect()

与 AdbController 接口完全兼容, 可直接替换到 TaskEngine 中使用.
"""

import time
import os
from typing import Optional, Tuple
import numpy as np

try:
    import mss
except ImportError:
    mss = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

from .logger import log_debug, log_info, log_error, log_warn


class DesktopController:
    """
    Windows 桌面/窗口控制器

    参数:
        window_title: 窗口标题 (模糊匹配), 为 None 则全屏模式
        region:       自定义裁剪区域 (x, y, w, h), 与全屏/窗口模式可叠加
        monitor:      mss 显示器编号 (全屏模式时使用, 0 = 全部, 1 = 主显示器)
    """

    def __init__(self, window_title: Optional[str] = None,
                 monitor: int = 0,
                 region: Optional[Tuple[int, int, int, int]] = None):
        self.window_title = window_title
        self.monitor = monitor
        self._win = None       # pygetwindow 窗口对象
        self._sct = None       # mss 截图对象
        self._region = region  # 自定义裁剪区域 (x, y, w, h), 坐标相对屏幕/窗口
        self._offset_x = 0     # 窗口左上角 X (窗口模式)
        self._offset_y = 0     # 窗口左上角 Y (窗口模式)

    # ── 连接管理 ────────────────────────────────────────

    def connect(self) -> bool:
        """初始化截图工具和鼠标键盘控制"""
        if mss is None:
            log_error("缺少依赖 mss, 请执行: pip install mss")
            return False
        if pyautogui is None:
            log_error("缺少依赖 pyautogui, 请执行: pip install pyautogui")
            return False

        # 关闭 pyautogui 的故障安全 (鼠标移到左上角不抛异常)
        pyautogui.FAILSAFE = False
        self._sct = mss.mss()

        if self.window_title:
            return self._find_window()

        # 叠加自定义区域偏移 (region 坐标相对于全屏或窗口)
        if self._region:
            self._offset_x += self._region[0]
            self._offset_y += self._region[1]
            log_info(f"操作区域: ({self._region[0]},{self._region[1]}) "
                     f"{self._region[2]}x{self._region[3]}")

        log_info("桌面控制器已就绪 (全屏模式)")
        return True

    def _find_window(self) -> bool:
        """通过标题查找并绑定窗口"""
        try:
            import pygetwindow as gw
        except ImportError:
            log_error("缺少依赖 pygetwindow, 请执行: pip install pygetwindow")
            return False

        windows = gw.getWindowsWithTitle(self.window_title)
        if not windows:
            log_error(f"未找到窗口: {self.window_title}")
            log_info("提示: 窗口标题支持模糊匹配, 如'记事本'可匹配'*无标题 - 记事本'")
            return False

        self._win = windows[0]
        if self._win.isMinimized:
            self._win.restore()
        self._win.activate()
        time.sleep(0.3)  # 等待窗口激活

        self._offset_x = self._win.left
        self._offset_y = self._win.top

        log_info(f"已绑定窗口: {self._win.title} "
                 f"({self._win.width}x{self._win.height})")
        return True

    def disconnect(self) -> bool:
        """释放资源"""
        self._sct = None
        self._win = None
        log_info("桌面控制器已断开")
        return True

    # ── 操作指令 ────────────────────────────────────────

    def screencap(self) -> Optional[np.ndarray]:
        """
        截取屏幕/窗口, 返回 BGR 格式 numpy array

        优先级: 自定义区域 > 窗口 > 全屏
        """
        try:
            if self._region:
                # 自定义区域 (_offset 已叠加 region 偏移)
                w, h = self._region[2], self._region[3]
                grab_region = {
                    "left": self._offset_x,
                    "top":  self._offset_y,
                    "width": w, "height": h,
                }
                img = np.array(self._sct.grab(grab_region))
            elif self._win:
                region = {
                    "left": self._win.left,
                    "top": self._win.top,
                    "width": self._win.width,
                    "height": self._win.height,
                }
                img = np.array(self._sct.grab(region))
            else:
                img = np.array(self._sct.grab(self._sct.monitors[self.monitor]))
            # mss 返回 BGRA (4 通道), 去掉 Alpha 通道, 保留 BGR
            return img[:, :, :3]
        except Exception as e:
            log_error(f"截屏失败: {e}")
            return None

    def click(self, x: int, y: int) -> bool:
        """点击坐标 (x, y), 自动加窗口偏移"""
        try:
            pyautogui.click(x + self._offset_x, y + self._offset_y)
            return True
        except Exception as e:
            log_error(f"点击失败: {e}")
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int,
              duration_ms: int = 300) -> bool:
        """滑动/拖拽: 从 (x1,y1) 拖到 (x2,y2)"""
        try:
            abs_x1, abs_y1 = x1 + self._offset_x, y1 + self._offset_y
            abs_x2, abs_y2 = x2 + self._offset_x, y2 + self._offset_y
            pyautogui.moveTo(abs_x1, abs_y1)
            pyautogui.drag(abs_x2 - abs_x1, abs_y2 - abs_y1,
                           duration=duration_ms / 1000.0)
            return True
        except Exception as e:
            log_error(f"滑动失败: {e}")
            return False

    def long_click(self, x: int, y: int, duration_ms: int = 1000) -> bool:
        """长按: 在 (x,y) 按住 duration_ms 毫秒"""
        try:
            abs_x, abs_y = x + self._offset_x, y + self._offset_y
            pyautogui.mouseDown(abs_x, abs_y)
            time.sleep(duration_ms / 1000.0)
            pyautogui.mouseUp()
            return True
        except Exception as e:
            log_error(f"长按失败: {e}")
            return False

    def input_key(self, key_code: int) -> bool:
        """发送按键 (兼容 Android keyevent 码的常用映射)"""
        # Android keyevent → pyautogui 键名
        key_map = {
            3: 'home', 4: 'backspace', 24: 'volumeup',
            25: 'volumedown', 66: 'enter', 67: 'backspace',
        }
        try:
            key = key_map.get(key_code, str(key_code))
            pyautogui.press(key)
            return True
        except Exception as e:
            log_error(f"按键 {key_code} 失败: {e}")
            return False

    def get_resolution(self) -> Optional[Tuple[int, int]]:
        """获取当前操作区域分辨率"""
        if self._region:
            return (self._region[2], self._region[3])
        if self._win:
            return (self._win.width, self._win.height)
        if self._sct:
            monitor = self._sct.monitors[self.monitor]
            return (monitor["width"], monitor["height"])
        return None

    @staticmethod
    def select_region():
        """弹出交互式选区窗口，用鼠标拖拽框选区域，返回 (x, y, w, h) 或 None"""
        import tkinter as tk

        result = [0, 0, 0, 0]

        root = tk.Tk()
        root.title("拖拽选择区域")
        root.attributes('-fullscreen', True)
        root.attributes('-alpha', 0.45)
        root.attributes('-topmost', True)
        root.configure(cursor='cross')

        canvas = tk.Canvas(root, bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(
            root, text="拖拽鼠标选择区域，松开确认 (ESC 取消)",
            font=('Microsoft YaHei', 16), fg='white', bg='#333'
        )
        label.place(relx=0.5, rely=0.03, anchor='center')

        rect_id = None
        text_id = None
        start_x = start_y = 0

        def on_press(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            if rect_id:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline='#ff3333', width=4
            )

        def on_drag(event):
            nonlocal text_id
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)
                w, h = abs(event.x - start_x), abs(event.y - start_y)
                if text_id:
                    canvas.delete(text_id)
                text_id = canvas.create_text(
                    min(start_x, event.x) + w / 2,
                    min(start_y, event.y) + h / 2 - 15,
                    text=f'{w} x {h}',
                    fill='#ff3333', font=('Consolas', 14, 'bold')
                )

        def on_release(event):
            result[0] = min(start_x, event.x)
            result[1] = min(start_y, event.y)
            result[2] = abs(event.x - start_x)
            result[3] = abs(event.y - start_y)
            root.destroy()

        def on_escape(event):
            result[2] = 0
            root.destroy()

        canvas.bind('<ButtonPress-1>', on_press)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        root.bind('<Escape>', on_escape)
        canvas.focus_set()

        root.mainloop()

        if result[2] > 10 and result[3] > 10:
            log_info(f"已选择区域: ({result[0]},{result[1]}) {result[2]}x{result[3]}")
            return tuple(result)
        log_info("区域选择已取消")
        return None

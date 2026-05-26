"""
ADB 控制器 — 通过 subprocess 调用 adb.exe 操控安卓设备

对应 C++ 的 Controller/AdbController.cpp

工作原理:
    每个操作 (点击/滑动/截屏等) 都通过 adb shell 命令发送到设备:
    
    点击:      adb -s {addr}:{port} shell input tap {x} {y}
    滑动:      adb -s {addr}:{port} shell input swipe {x1} {y1} {x2} {y2} {ms}
    截屏:      adb -s {addr}:{port} shell screencap /sdcard/screen.png
             → adb -s {addr}:{port} pull /sdcard/screen.png ./
             → cv2.imread("./screen.png")
"""

import subprocess
import os
import time
from typing import Optional, Tuple
import cv2
import numpy as np

from .logger import log_debug, log_info, log_error


def _find_adb() -> str:
    """
    查找 adb.exe 的路径
    优先级: 1. 项目根目录 ./adb/adb.exe  2. PATH 环境变量
    """
    # 尝试相对于当前文件的路径
    local_adb = os.path.join(os.path.dirname(__file__), "..", "adb", "adb.exe")
    if os.path.exists(local_adb):
        return os.path.abspath(local_adb)

    # 尝试常见位置
    for candidate in [
        r".\adb\adb.exe",
        r"D:\ai\OpenAR-main\OpenAR-main\3rdparty\bin\adb\adb.exe",
        r"C:\adb\adb.exe",
    ]:
        if os.path.exists(candidate):
            return os.path.abspath(candidate)

    # 最后尝试 PATH 中的 adb
    return "adb"


class AdbController:
    """
    ADB 设备控制器
    
    使用示例:
        ctrl = AdbController(adb_path="127.0.0.1", adb_port=16416)
        ctrl.connect()
        ctrl.click(500, 800)
        frame = ctrl.screencap()
        ctrl.disconnect()
    """

    def __init__(self, adb_path: str = "127.0.0.1", adb_port: int = 5555,
                 adb_exe: Optional[str] = None):
        """
        参数:
            adb_path:  设备 IP 地址或序列号 (默认 127.0.0.1)
            adb_port:  ADB 端口 (MuMu 模拟器默认 16384 + 实例编号*32, 如实例0=16384)
            adb_exe:   adb.exe 路径 (为 None 则自动查找)
        """
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.adb_exe = adb_exe or _find_adb()
        self._device_spec = f"{adb_path}:{adb_port}"
        self._connected = False

    # ── 连接管理 ────────────────────────────────────────

    def connect(self) -> bool:
        """
        连接设备 — 对应 C++ 的 connect()
        执行: adb connect 127.0.0.1:16416
        """
        cmd = f'"{self.adb_exe}" connect {self._device_spec}'
        log_debug(cmd)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        output = (result.stdout or "") + (result.stderr or "")
        if "error" in output.lower() or "cannot" in output.lower():
            log_error(f"无法连接 {self._device_spec}: {output.strip()}")
            return False
        self._connected = True
        log_info(f"已连接到设备 {self._device_spec}")
        return True

    def disconnect(self) -> bool:
        """断开连接"""
        if not self._connected:
            return True
        cmd = f'"{self.adb_exe}" disconnect {self._device_spec}'
        subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
        # 清理临时截图
        if os.path.exists("./screen.png"):
            os.remove("./screen.png")
        self._connected = False
        log_info(f"已断开 {self._device_spec}")
        return True

    # ── 操作指令 ────────────────────────────────────────

    def _adb_shell(self, shell_cmd: str) -> str:
        """
        执行 adb shell 命令
        adb -s 127.0.0.1:16416 shell {shell_cmd}
        """
        cmd = f'"{self.adb_exe}" -s {self._device_spec} shell {shell_cmd}'
        log_debug(cmd)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        return ((result.stdout or "") + (result.stderr or "")).strip()

    def click(self, x: int, y: int) -> bool:
        """
        点击屏幕坐标 (x, y)
        adb shell input tap {x} {y}
        """
        output = self._adb_shell(f"input tap {x} {y}")
        if "not found" in output.lower():
            log_error(f"点击 ({x},{y}) 失败: {output}")
            return False
        return True

    def long_click(self, x: int, y: int, duration_ms: int = 1000) -> bool:
        """
        长按 — 通过 swipe 同点滑动模拟
        adb shell input swipe {x} {y} {x} {y} {duration_ms}
        """
        output = self._adb_shell(
            f"input swipe {x} {y} {x} {y} {duration_ms}"
        )
        if "not found" in output.lower():
            log_error(f"长按 ({x},{y}) 失败: {output}")
            return False
        return True

    def swipe(self, x1: int, y1: int, x2: int, y2: int,
              duration_ms: int = 300) -> bool:
        """
        滑动
        adb shell input swipe {x1} {y1} {x2} {y2} {duration_ms}
        """
        output = self._adb_shell(
            f"input swipe {x1} {y1} {x2} {y2} {duration_ms}"
        )
        if "not found" in output.lower():
            log_error(f"滑动失败: {output}")
            return False
        return True

    def input_key(self, key_code: int) -> bool:
        """
        发送按键事件
        adb shell input keyevent {key_code}
        
        常用 key_code:  3=HOME 4=BACK 24=音量+ 25=音量- 26=电源
        """
        output = self._adb_shell(f"input keyevent {key_code}")
        if "not found" in output.lower():
            log_error(f"按键 {key_code} 失败: {output}")
            return False
        return True

    def screencap(self) -> Optional[np.ndarray]:
        """
        截取设备屏幕并返回 OpenCV 图像 (numpy array)

        对应 C++ 的 AdbController::screencap():
            1. adb shell screencap /sdcard/screen.png   (设备端截图)
            2. adb pull /sdcard/screen.png ./            (拉取到本地)
            3. cv::imread("./screen.png")                (OpenCV 读取)

        返回: numpy ndarray (BGR 格式) 或 None (失败时)
        """
        save_path = "/sdcard/screen.png"
        local_path = "./screen.png"

        # 步骤1: 设备端截图
        cmd1 = f'"{self.adb_exe}" -s {self._device_spec} shell screencap {save_path}'
        log_debug(cmd1)
        r1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        if "error" in ((r1.stdout or "") + (r1.stderr or "")).lower():
            log_error("设备截图失败")
            return None

        # 步骤2: 拉取截图到本地
        cmd2 = f'"{self.adb_exe}" -s {self._device_spec} pull {save_path} {local_path}'
        log_debug(cmd2)
        r2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        if "error" in ((r2.stdout or "") + (r2.stderr or "")).lower():
            log_error("拉取截图失败")
            return None

        # 步骤3: OpenCV 读取
        img = cv2.imread(local_path)
        if img is None:
            log_error("OpenCV 无法读取截图")
            return None

        return img

    def get_resolution(self) -> Optional[Tuple[int, int]]:
        """
        获取设备屏幕分辨率
        返回: (width, height) 或 None
        """
        output = self._adb_shell("wm size")
        # 输出格式: "Physical size: 1080x1920"
        try:
            size_str = output.split(":")[-1].strip()
            w, h = map(int, size_str.split("x"))
            return w, h
        except (ValueError, IndexError):
            log_error(f"获取分辨率失败: {output}")
            return None

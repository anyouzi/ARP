"""
OpenAR-Python — 图像识别安卓自动化框架

原项目: https://github.com/sakura2107/OpenAR  (C++ / MIT 协议)
本版本: Python + OpenCV + ADB subprocess, 支持桌面/安卓双模式.

快速上手:
    python demo_pcr.py          # 演示脚本
    python demo_desktop.py      # 桌面自动化演示
    python launcher.py task.json  # JSON 驱动模式
"""

import importlib

_exports = {
    "AdbController":        "controller",
    "DesktopController":    "desktop_controller",
    "TemplateMatcher":      "recognition",
    "ARProject":            "config",
    "ARTask":               "config",
    "ARBlock":              "config",
    "ARLoopGroup":          "config",
    "ARCode":               "config",
    "TaskEngine":           "engine",
    "log_info":             "logger",
    "log_debug":            "logger",
    "log_error":            "logger",
    "log_warn":             "logger",
}

def __getattr__(name):
    if name in _exports:
        mod = importlib.import_module(f".{_exports[name]}", __package__)
        return getattr(mod, name)
    raise AttributeError(f"module 'openar' has no attribute '{name}'")

__version__ = "0.2.0"

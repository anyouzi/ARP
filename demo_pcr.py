"""
演示脚本 — 对应 C++ PCRDemo 项目

展示如何使用 OpenAR-Python 的 API 直接编写自动化脚本。
模式: 硬编码逻辑 (写代码, 非 JSON 配置)

运行前请修改 CONFIG 中的参数为你实际的设备配置!
"""

import sys
import os

# 确保能找到 openar 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openar import AdbController, TemplateMatcher, log_info, log_debug, log_error

# ══════════════════════════════════════════════════════════════
#  配置区 — 请根据你的实际设备修改
# ══════════════════════════════════════════════════════════════

CONFIG = {
    "adb_host":     "127.0.0.1",     # ADB 地址 (真机通常填 IP)
    "adb_port":     16416,           # ADB 端口
    # MuMu 模拟器端口: 16384 + 实例编号*32 (实例0=16384, 实例1=16416...)
    # 雷电模拟器端口: 5555 (默认)

    "operate_duration": 200,  # 每轮操作间隔 (毫秒)
    "run_max_times":    200,  # 最大循环次数 (超时保护)
}


def main():
    """
    演示: 连接设备 → 执行一个简单的找图+点击流程

    你可以模仿这个结构编写自己的游戏脚本:
        while 没找到目标:
            截屏
            匹配各种可能的 UI 元素
            匹配到了就点击
            匹配到"主界面特征" → 退出循环
    """

    print("=" * 50)
    print("  OpenAR-Python 演示脚本")
    print("=" * 50)
    print()
    print("本演示将:")
    print("  1. 连接 ADB 设备")
    print("  2. 获取屏幕分辨率")
    print("  3. 演示截屏 + 模板匹配流程")
    print("  4. 断开连接")
    print()

    # ── 步骤1: 创建并连接控制器 ──
    ctrl = AdbController(
        adb_path=CONFIG["adb_host"],
        adb_port=CONFIG["adb_port"]
    )

    if not ctrl.connect():
        print("❌ 连接设备失败! 请检查:")
        print("  - 模拟器/手机是否已开启 USB 调试")
        print("  - ADB 地址和端口是否正确")
        print("  - adb.exe 是否在 PATH 或 ./adb/adb.exe")
        return

    # ── 步骤2: 获取分辨率 ──
    resolution = ctrl.get_resolution()
    if resolution:
        print(f"设备分辨率: {resolution[0]} x {resolution[1]}")
    else:
        print("⚠ 无法获取分辨率, 继续...")

    # ── 步骤3: 截屏并保存 (让你看看效果) ──
    print()
    print("正在截屏...")
    screen = ctrl.screencap()
    if screen is not None:
        import cv2
        cv2.imwrite("./demo_screenshot.png", screen)
        print(f"✓ 截图已保存到: {os.path.abspath('./demo_screenshot.png')}")

    # ── 步骤4: 演示模板匹配 ──
    # 如果你有模板图片, 可以取消下面的注释来测试
    print()
    print("提示: 如果你有模板图片 (如 res/button.png), 可以取消注释来测试匹配:")
    print()
    print("  matcher = TemplateMatcher()")
    print("  frame = ctrl.screencap()")
    print("  result = matcher.find(frame, 'res/button.png', 0.95)")
    print("  if result:")
    print("      ctrl.click(result.x, result.y)")
    print()
    print("─" * 50)
    print("  下面是一个完整的自动点击循环示例:")
    print("─" * 50)

    matcher = TemplateMatcher()

    # 示例: 在屏幕左上角区域找一个已知图标的示例
    # (如果你没有模板图, 这步会跳过)
    template_path = "./res/example.png"
    if os.path.exists(template_path):
        print(f"找到模板 {template_path}, 执行匹配演示...")
        frame = ctrl.screencap()
        result = matcher.find(frame, template_path, threshold=0.9)
        if result:
            print(f"匹配成功! 坐标: ({result.x}, {result.y})")
            # ctrl.click(result.x, result.y)  # 取消注释以实际点击
        else:
            print("未匹配到目标 (可能是模板图与屏幕内容不匹配)")
    else:
        print(f"模板文件不存在: {template_path}")
        print("请将你的模板 PNG 放到 res/ 目录下, 然后修改上面的路径")

    # ── 步骤5: 断开 ──
    ctrl.disconnect()
    print()
    print("演示结束。")


if __name__ == "__main__":
    main()

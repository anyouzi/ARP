"""
桌面自动化演示脚本 — 展示 DesktopController 的使用

运行前准备:
    1. pip install mss pyautogui pygetwindow
    2. 准备好模板图片放到 res/ 目录
    3. 如果使用窗口模式, 保持目标窗口打开且可见

用法:
    python demo_desktop.py                  # 全屏模式
    python demo_desktop.py --loop           # 持续监视循环 (Ctrl+C 退出)
    python demo_desktop.py --select         # 运行前交互框选区域
    python demo_desktop.py --region 100,200,400,300   # 指定裁剪区域
    python demo_desktop.py --window "记事本"       # 窗口模式
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openar import DesktopController, TemplateMatcher, log_info, log_error


def main():
    parser = argparse.ArgumentParser(description="OpenAR 桌面自动化演示")
    parser.add_argument("--window", "-w", type=str, default=None,
                        help="窗口标题 (如 '记事本'), 不指定则为全屏模式")
    parser.add_argument("--select", "-s", action="store_true",
                        help="运行前弹出交互式选框, 拖拽鼠标框定区域")
    parser.add_argument("--region", "-r", type=str, default=None,
                        help="指定裁剪区域 (格式: x,y,w,h)")
    parser.add_argument("--loop", "-l", action="store_true",
                        help="持续监视模式 (循环截屏+匹配, Ctrl+C 退出)")
    parser.add_argument("--template", "-t", type=str, default="./res/example.png",
                        help="模板图片路径 (默认 ./res/example.png)")
    parser.add_argument("--threshold", type=float, default=0.9,
                        help="匹配阈值 0~1 (默认 0.9)")
    parser.add_argument("--interval", "-i", type=int, default=200,
                        help="每轮循环间隔毫秒 (默认 200)")
    parser.add_argument("--click", action="store_true",
                        help="监视模式下匹配成功后自动点击")
    args = parser.parse_args()

    print("=" * 50)
    print("  OpenAR-Python 桌面自动化演示")
    print("=" * 50)
    print()
    if args.loop:
        print(f"监视模式: 持续循环 (间隔 {args.interval}ms, 模板 {args.template})")
        print(f"匹配阈值: {args.threshold}  |  点击: {'是' if args.click else '否'}")
        print()

    if args.window:
        print(f"模式: 窗口模式 (目标: {args.window})")
    else:
        print("模式: 全屏模式")
    print()

    # 处理自定义区域
    region = None
    if args.region:
        try:
            parts = [int(x.strip()) for x in args.region.split(",")]
            if len(parts) == 4:
                region = tuple(parts)
                print(f"自定义区域: ({region[0]},{region[1]}) {region[2]}x{region[3]}")
        except ValueError:
            print("错误: --region 格式应为 x,y,w,h (如 --region 100,200,400,300)")
            return

    if args.select:
        print("请在弹出窗口中拖拽鼠标选择区域...")
        region = DesktopController.select_region()
        if region is None:
            print("区域选择已取消")
            return
        print(f"已选择区域: ({region[0]},{region[1]}) {region[2]}x{region[3]}")

    # 创建控制器
    ctrl = DesktopController(window_title=args.window, region=region)

    if not ctrl.connect():
        print("初始化失败!")
        print("  请确保已安装: pip install mss pyautogui pygetwindow")
        return

    # 获取分辨率
    resolution = ctrl.get_resolution()
    if resolution:
        print(f"操作区域分辨率: {resolution[0]} x {resolution[1]}")

    print()

    if args.loop:
        # ── 持续监视模式 ──
        _run_loop(ctrl, args)
    else:
        # ── 单次演示模式 ──
        _run_demo(ctrl, args)

    ctrl.disconnect()
    print()
    print("演示结束。")


def _run_demo(ctrl, args):
    """单次截屏 + 匹配演示"""
    print("正在截屏...")
    screen = ctrl.screencap()
    if screen is not None:
        import cv2
        save_path = "./demo_desktop_screenshot.png"
        cv2.imwrite(save_path, screen)
        print(f"截图已保存到: {os.path.abspath(save_path)}")
    else:
        print("截屏失败")
        return

    # 模板匹配演示
    print()
    print("-" * 50)
    print("  模板匹配演示:")
    print("-" * 50)

    matcher = TemplateMatcher()
    template_path = args.template

    if os.path.exists(template_path):
        result = matcher.find(screen, template_path, threshold=args.threshold)
        if result:
            print(f"匹配成功! 坐标: ({result.x}, {result.y})")
            print("  (取消下方注释以实际点击)")
            # ctrl.click(result.x, result.y)
        else:
            print("未匹配到目标")
    else:
        print(f"模板文件不存在: {template_path}")
        print("请将模板 PNG 放到 res/ 目录下")


def _run_loop(ctrl, args):
    """持续监视循环"""
    import time as _time
    matcher = TemplateMatcher()
    template_path = args.template

    if not os.path.exists(template_path):
        print(f"模板文件不存在: {template_path}")
        return

    print("开始监视... (按 Ctrl+C 退出)")
    print()

    count = 0
    hits = 0
    try:
        while True:
            count += 1
            frame = ctrl.screencap()
            if frame is None:
                print("[ERROR] 截屏失败")
                _time.sleep(args.interval / 1000)
                continue

            result = matcher.find(frame, template_path, threshold=args.threshold)
            if result:
                hits += 1
                ts = _time.strftime("%H:%M:%S")
                print(f"[{ts}] #{count} 匹配成功! ({result.x}, {result.y})  "
                      f"命中率: {hits}/{count}")
                if args.click:
                    ctrl.click(result.x, result.y)
                    print(f"          已点击")
            else:
                if count % 10 == 0:
                    ts = _time.strftime("%H:%M:%S")
                    print(f"[{ts}] #{count} 未匹配  命中率: {hits}/{count}")

            _time.sleep(args.interval / 1000)

    except KeyboardInterrupt:
        print()
        print(f"监视结束 — 共 {count} 轮, 命中 {hits} 次")


if __name__ == "__main__":
    main()

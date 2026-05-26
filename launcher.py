"""
JSON 配置启动器 — 对应 C++ 的 ARLauncher

用法:
    python launcher.py                    # 自动扫描当前目录下的 .json 文件
    python launcher.py task.json          # 指定 JSON 文件
    python launcher.py task1.json task2.json  # 多个文件按顺序执行

JSON 结构示例见 example.json
"""

import sys
import os
from glob import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openar import ARProject, AdbController, DesktopController, TaskEngine, log_info, log_error


def main():
    if len(sys.argv) > 1:
        # 用户指定了 JSON 文件
        json_files = [f for f in sys.argv[1:] if f.endswith(".json")]
    else:
        # 自动扫描当前目录
        json_files = glob("*.json")

    if not json_files:
        print("错误: 没有找到 JSON 配置文件!")
        print("用法: python launcher.py <config.json>")
        print("或: 将 .json 文件放在当前目录下")
        return

    print(f"找到 {len(json_files)} 个配置文件: {json_files}")
    print()

    for json_file in json_files:
        print(f"── 加载: {json_file} ──")

        try:
            project = ARProject.from_json_file(json_file)
        except Exception as e:
            log_error(f"加载 JSON 失败: {e}")
            continue

        print(f"  项目: {project.project_name}")
        if project.controller_type == 1:
            print(f"  模式: 桌面 | {'窗口: '+project.device_path if project.device_path else '全屏'}")
        else:
            print(f"  设备: {project.adb_path}:{project.adb_port}")
        print(f"  任务数: {len(project.tasks)}")

        # 根据 controller_type 创建对应控制器
        if project.controller_type == 1:
            # 桌面模式
            region = None
            if project.desktop_region:
                try:
                    parts = [int(x.strip()) for x in project.desktop_region.split(",")]
                    if len(parts) == 4:
                        region = tuple(parts)
                except ValueError:
                    pass
            ctrl = DesktopController(
                window_title=project.device_path or None,
                monitor=project.device_index,
                region=region,
            )
        else:
            # ADB 模式 (默认)
            ctrl = AdbController(
                adb_path=project.adb_path,
                adb_port=project.adb_port
            )

        if not ctrl.connect():
            log_error("连接设备失败, 跳过此配置")
            continue

        # 创建引擎并执行
        engine = TaskEngine(project, ctrl)
        engine.run()

        # 断开
        ctrl.disconnect()
        print()

    print("全部完成。")


if __name__ == "__main__":
    main()

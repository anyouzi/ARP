"""
数据模型 — 对应 C++ 的 Data/ARData.h + Data/ARJson.h

层级结构:
    ARProject (项目)
      └─ ARTask[] (任务列表)
           └─ ARLoopGroup[] (循环组)
                └─ ARBlock[] (代码块)
                     └─ ARCode[] (单条指令)
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ARCode:
    """
    单条指令 — 对应 C++ 的 class ARCode

    first_value:  触发条件类型
        0 = 无条件直接执行
        1 = 图像识别匹配后执行
        2 = 文字识别 (暂不支持)
        3 = 超时触发

    second_value: 执行动作类型
        0 = 空操作
        1 = 点击 (匹配坐标 + click_x/click_y 偏移)
        2 = 滑动
        3 = 长按
        4 = 按键
        5 = 等待 sleep_time 毫秒
        6 = 退出当前 Block 循环 (stop_loop)
        7 = 退出当前 Task (return)
        8 = 退出程序 (exit)
    """
    code_id: int = 0
    first_value: int = 0          # 条件类型
    second_value: int = 0         # 动作类型

    image_path: str = ""          # 模板图片路径
    threshold: float = 0.95       # 匹配阈值

    text: str = ""                # 文字识别文本 (暂未实现)

    time_out: int = 0             # 超时时间 (毫秒)

    # ---- 点击相关 ----
    click_x: int = 0              # 相对于匹配点的 X 偏移
    click_y: int = 0              # 相对于匹配点的 Y 偏移

    # ---- 滑动相关 ----
    swipe_x_1: int = 0
    swipe_y_1: int = 0
    swipe_x_2: int = 0
    swipe_y_2: int = 0
    swipe_time: int = 0           # 滑动持续时间 (毫秒)

    # ---- 长按相关 ----
    long_click_x: int = 0
    long_click_y: int = 0
    long_click_time: int = 0      # 长按持续时间 (毫秒)
    click_x_max: int = 0
    click_y_max: int = 0
    swipe_x_1_max: int = 0
    swipe_y_1_max: int = 0
    swipe_x_2_max: int = 0
    swipe_y_2_max: int = 0
    swipe_time_max: int = 0
    sleep_time_max: int = 0

    # ---- 按键相关 ----
    key_code: int = 0             # Android keyevent 码

    # ---- 等待相关 ----
    sleep_time: int = 0           # 等待时间 (毫秒)

    @classmethod
    def from_dict(cls, d: dict) -> "ARCode":
        """从字典创建 ARCode (用于 JSON 加载)"""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ARBlock:
    """
    代码块 — 一个 Block = 一个循环体
    
    引擎会对 Block 内所有 Code 循环执行:
        do {
            截屏
            依次检查每条 Code 的条件 → 条件满足则执行对应动作
        } while (stop_condition == False)
    
    stop_condition 由 second_value=6 的 Code 触发
    """
    block_id: int = 0
    block_name: str = "New Block"
    codes: List[ARCode] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ARBlock":
        codes = [ARCode.from_dict(c) for c in d.get("codes", [])]
        return cls(
            block_id=d.get("block_id", 0),
            block_name=d.get("block_name", "New Block"),
            codes=codes
        )


@dataclass
class ARLoopGroup:
    """
    循环组 — Task 内的外层循环

    一个 LoopGroup 包含多个 Block，按顺序执行。
    执行完一轮所有 Block 后，loop_count 减 1，重复直到：
      - loop_count 耗尽 (0 表示无限循环)
      - 停止条件满足 (图片匹配/文字识别/超时)
      - 全局停止标志被设置

    stop_condition_type:
        0 = 仅靠循环次数 (无条件)
        1 = 图像匹配满足时停止
        2 = 文字识别命中时停止
        3 = 超时时停止
    """
    loop_id: int = 0
    loop_name: str = "Loop 1"
    loop_count: int = 1          # 循环次数 (0=无限循环直到条件满足)

    # 停止条件
    stop_condition_type: int = 0 # 0=次数, 1=图片, 2=文字, 3=超时
    stop_image_path: str = ""    # 停止条件图片路径
    stop_threshold: float = 0.9  # 图片匹配阈值
    stop_text: str = ""          # 停止条件文字
    stop_time_out: int = 0       # 超时时间 (毫秒)

    blocks: List[ARBlock] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ARLoopGroup":
        blocks = [ARBlock.from_dict(b) for b in d.get("blocks", [])]
        return cls(
            loop_id=d.get("loop_id", 0),
            loop_name=d.get("loop_name", "Loop 1"),
            loop_count=d.get("loop_count", 1),
            stop_condition_type=d.get("stop_condition_type", 0),
            stop_image_path=d.get("stop_image_path", ""),
            stop_threshold=d.get("stop_threshold", 0.9),
            stop_text=d.get("stop_text", ""),
            stop_time_out=d.get("stop_time_out", 0),
            blocks=blocks,
        )


@dataclass
class ARTask:
    """
    任务 — 包含多个 LoopGroup，按顺序执行

    兼容旧格式: 如果 JSON 有 "blocks" 但没有 "loop_groups"，
    自动包装为单个 ARLoopGroup (loop_count=1)。
    """
    task_id: int = 0
    task_name: str = "New Task"
    loop_groups: List[ARLoopGroup] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ARTask":
        loop_groups = [ARLoopGroup.from_dict(lg) for lg in d.get("loop_groups", [])]
        # 向后兼容旧格式: 如果无 loop_groups 但有 blocks，自动包装
        if not loop_groups and d.get("blocks"):
            blocks = [ARBlock.from_dict(b) for b in d.get("blocks", [])]
            loop_groups = [ARLoopGroup(
                loop_id=1, loop_name="Loop 1", loop_count=1,
                blocks=blocks
            )]
        return cls(
            task_id=d.get("task_id", 0),
            task_name=d.get("task_name", "New Task"),
            loop_groups=loop_groups
        )


@dataclass
class ARProject:
    """
    项目 — 顶层配置 + 多个任务

    对应 C++ 的 ARProject
    """
    project_id: int = 0
    project_name: str = "New Project"

    # ---- 设备连接 ----
    adb_path: str = "127.0.0.1"   # ADB 地址 / 设备序列号
    adb_port: int = 5555           # ADB 端口

    # ---- 控制类型 (暂不支持 MuMu API, 仅 ADB) ----
    device_type: int = 0
    controller_type: int = 0       # 0=ADB, 1=Desktop
    image_recognition_type: int = 0

    # ---- MuMu 专用 (可选) ----
    # 桌面模式下复用:
    device_path: str = ""          # Desktop: 窗口标题 (如 "记事本"); ADB: MuMu模拟器路径
    device_index: int = 0          # Desktop: 显示器编号 (0=全部,1=主); ADB: MuMu实例号
    desktop_region: str = ""       # Desktop 裁剪区域 "x,y,w,h" (空=不使用)

    # ---- 运行参数 ----
    duration_time: int = 200       # 每轮循环间隔 (毫秒)
    run_max_times: int = 200       # 最大循环次数

    tasks: List[ARTask] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ARProject":
        """从字典创建 ARProject"""
        tasks = [ARTask.from_dict(t) for t in d.get("tasks", [])]
        return cls(
            project_id=d.get("project_id", 0),
            project_name=d.get("project_name", "New Project"),
            adb_path=d.get("adb_path", "127.0.0.1"),
            adb_port=d.get("adb_port", 5555),
            device_type=d.get("device_type", 0),
            controller_type=d.get("controller_type", 0),
            image_recognition_type=d.get("image_recognition_type", 0),
            device_path=d.get("device_path", ""),
            device_index=d.get("device_index", 0),
            desktop_region=d.get("desktop_region", ""),
            duration_time=d.get("duration_time", 200),
            run_max_times=d.get("run_max_times", 200),
            tasks=tasks
        )

    @classmethod
    def from_json_file(cls, path: str) -> "ARProject":
        """从 JSON 文件加载 ARProject — 对应 C++ 的 loadJsonFile()"""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_json_file(self, path: str):
        """保存为 JSON 文件 — 对应 C++ 的 saveJsonFile()"""
        # 将 dataclass 转为纯字典
        def convert(obj):
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            if hasattr(obj, "__dataclass_fields__"):
                return {k: convert(v) for k, v in obj.__dict__.items()}
            return obj
        with open(path, "w", encoding="utf-8") as f:
            json.dump(convert(self), f, indent=2, ensure_ascii=False)

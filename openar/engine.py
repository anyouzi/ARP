"""
任务引擎 — JSON 驱动的工作流执行器

对应 C++ 的 ARLauncher/ARLTaskNode.cpp + ARLTaskPipline.cpp

执行模型:
    对每个 Task:
        对每个 Block (一个 Block = 一个 do-while 循环):
            do {
                截屏一次
                按顺序处理 Block 内每条 Code:
                    判断 first_value (条件) → 满足则执行 second_value (动作)
            } while (stop_condition == False)

    控制流 Code (second_value):
        6 = stop_loop   → 跳出当前 Block 循环
        7 = return      → 结束当前 Task
        8 = exit        → 退出整个程序
"""

import time
from typing import Optional, Dict

from .config import ARProject, ARTask, ARBlock, ARCode
from .controller import AdbController
from .recognition import TemplateMatcher
from .logger import log_info, log_debug, log_error, log_warn


class TaskEngine:
    """
    任务管线引擎

    用法:
        engine = TaskEngine(project, controller)
        engine.run()
    """

    _ocr_reader = None  # 进程级缓存, 仅初始化一次
    def __init__(self, project: ARProject, controller: AdbController):
        """
        参数:
            project:    ARProject 对象 (通常从 JSON 加载)
            controller: 已连接的 AdbController
        """
        self.project = project
        self.controller = controller
        self.matcher = TemplateMatcher()

        # 运行参数
        self.duration = project.duration_time   # 每轮间隔 (ms)
        self.max_times = project.run_max_times  # 最大循环次数

        # 图像缓存: 加载 JSON 中所有用到的模板图
        self._image_pool: Dict[str, "np.ndarray"] = {}
        self._load_all_images()

    def _load_all_images(self):
        """预加载 JSON 中所有引用的模板图片"""
        import cv2
        for task in self.project.tasks:
            for block in task.blocks:
                for code in block.codes:
                    if code.first_value != 1:
                        continue
                    if code.image_path in self._image_pool:
                        continue
                    img = cv2.imread(code.image_path)
                    if img is None:
                        log_error(f"无法加载图片: {code.image_path}")
                    else:
                        self._image_pool[code.image_path] = img
                        log_debug(f"已加载模板: {code.image_path}")

    def run(self):
        """
        按顺序执行所有 Task (对应 C++ ARLTaskPipline::play)
        """
        log_info(f"开始执行项目: {self.project.project_name}")
        log_info(f"任务数: {len(self.project.tasks)}")

        for task in self.project.tasks:
            self._execute_task(task)

        log_info("全部任务执行完毕")

    def _execute_task(self, task: ARTask):
        """
        执行单个 Task (对应 C++ ARLTaskNode::play)

        一个 Task 包含多个 Block, 按顺序执行。
        如果某个 Block 触发 return (second_value=7), 则提前结束本 Task。
        """
        log_info(f"  ── 任务: {task.task_name} (ID={task.task_id}) ──")

        for block in task.blocks:
            early_return = self._execute_block(block)
            if early_return:
                log_info(f"    任务 {task.task_name} 提前结束 (return)")
                return

    def _execute_block(self, block: ARBlock) -> bool:
        """
        执行单个 Block — 核心循环体

        对应 C++ ARLTaskNode::playPerLoopingBlock

        返回: True 表示触发了 return (应结束当前 Task)
              False 表示 Block 正常结束
        """
        stop_condition = False
        times = 0
        block_start = time.time()

        while not stop_condition:
            # ── 超时保护 ──
            times += 1
            if times > self.max_times:
                log_error(f"Block '{block.block_name}' 执行超时, 强制退出!")
                return True

            # ── 每轮间隔 ──
            time.sleep(self.duration / 1000.0)

            # ── 截屏一次 (整个 Block 共用这帧) ──
            frame = self.controller.screencap()
            if frame is None:
                log_error("截屏失败, 退出任务")
                return True

            # ── 遍历 Block 内每条 Code ──
            for code in block.codes:
                # 判断条件是否满足
                if not self._check_condition(code, frame,
                                              int((time.time() - block_start) * 1000)):
                    continue

                # 条件满足 → 执行动作 → 检查控制流返回值
                action_result = self._execute_action(code, frame)
                if action_result == "return":
                    return True
                if action_result == "stop_loop":
                    stop_condition = True
                    break
                if action_result == "exit":
                    log_info("程序退出 (exit)")
                    import sys
                    sys.exit(0)

        return False

    def _check_condition(self, code: ARCode, frame, elapsed_ms: int = 0) -> bool:
        """
        判断 Code 的触发条件是否满足

        first_value:
            0 → 无条件, 直接执行
            1 → 图像识别: 在 frame 中匹配 code.image_path
            2 → 文字识别 (未实现)
            3 → 超时触发 (暂未实现)
        """
        if code.first_value == 0:
            return True   # 无条件执行

        if code.first_value == 1:
            # ── 图像识别 ──
            template = self._image_pool.get(code.image_path)
            if template is None:
                log_warn(f"模板未加载: {code.image_path}")
                return False
            # 这里用预加载的 template 直接匹配, 不走文件路径
            import cv2
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= code.threshold:
                h, w = template.shape[:2]
                # 将匹配结果暂存到 code 的临时属性 (供动作使用)
                code._match_x = max_loc[0] + w // 2
                code._match_y = max_loc[1] + h // 2
                return True
            return False

        if code.first_value == 2:
            # ──── 文字识别 ────
            if not code.text:
                log_warn("文字识别: 未设置识别文本")
                return False
            try:
                import easyocr
                if TaskEngine._ocr_reader is None:
                    log_info("    初始化 OCR 引擎 (仅首次)...")
                    TaskEngine._ocr_reader = easyocr.Reader(
                        ['ch_sim', 'en'], gpu=False, verbose=False)
                results = TaskEngine._ocr_reader.readtext(frame)
                for (bbox, txt, conf) in results:
                    if code.text in txt:
                        x = int((bbox[0][0] + bbox[2][0]) / 2)
                        y = int((bbox[0][1] + bbox[2][1]) / 2)
                        code._match_x = x
                        code._match_y = y
                        log_debug(f"    文字识别命中: {txt} @ ({x},{y})")
                        return True
                return False
            except ImportError:
                log_error("文字识别需要: pip install easyocr")
                return False

        if code.first_value == 3:
            # ──── 超时触发 ────
            if code.time_out <= 0:
                return False
            return elapsed_ms >= code.time_out

        return False

    def _execute_action(self, code: ARCode, frame) -> Optional[str]:
        """
        执行 Code 的动作

        second_value:
            0 → 空操作
            1 → 点击 (匹配坐标 + 偏移)
            2 → 滑动
            3 → 长按
            4 → 按键
            5 → 等待
            6 → stop_loop (退出 Block 循环)
            7 → return (退出 Task)
            8 → exit (退出程序)

        返回: "stop_loop" / "return" / "exit" / None
        """
        if code.second_value == 0:
            pass  # 空操作

        elif code.second_value == 1:
            # ── 点击: 匹配点坐标 + 偏移 ──
            x = getattr(code, "_match_x", 0) + code.click_x
            y = getattr(code, "_match_y", 0) + code.click_y
            log_debug(f"    点击 ({x}, {y})")
            self.controller.click(x, y)

        elif code.second_value == 2:
            # ── 滑动 ──
            log_debug(f"    滑动 ({code.swipe_x_1},{code.swipe_y_1}) → "
                      f"({code.swipe_x_2},{code.swipe_y_2})")
            self.controller.swipe(
                code.swipe_x_1, code.swipe_y_1,
                code.swipe_x_2, code.swipe_y_2,
                code.swipe_time
            )

        elif code.second_value == 3:
            # ---- 长按 ----
            x = getattr(code, "_match_x", 0) + code.click_x
            y = getattr(code, "_match_y", 0) + code.click_y
            log_debug(f"    长按 ({x},{y}) {code.sleep_time}ms")
            self.controller.long_click(x, y, code.sleep_time)


        elif code.second_value == 4:
            # ── 按键 ──
            log_debug(f"    按键 {code.key_code}")
            self.controller.input_key(code.key_code)

        elif code.second_value == 5:
            # ── 等待 ──
            log_debug(f"    等待 {code.sleep_time}ms")
            time.sleep(code.sleep_time / 1000.0)

        elif code.second_value == 6:
            # ── 退出当前 Block 循环 ──
            return "stop_loop"

        elif code.second_value == 7:
            # ── 退出当前 Task ──
            return "return"

        elif code.second_value == 8:
            # ── 退出程序 ──
            return "exit"

        return None

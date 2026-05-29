"""OpenAR 工作流编辑器 — 可视化编辑 · 截图模板 · 导入导出"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json, os, sys, shutil, zipfile, time, threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class WorkflowEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenAR 工作流编辑器")
        self.root.geometry("1200x700")
        self._current_file = None
        self._project_root = tk.StringVar(value=".")
        self.data = self._default_project()
        self._build_ui()
        self._init_default_templates()
        self._refresh_all()

    @property
    def _data_dir(self):
        """当前项目图片目录: data/项目名/"""
        name = self.data.get("project_name", "untitled")
        return os.path.join(self._project_root.get(), "data", name)

    def _default_project(self):
        return {
            "project_id": 1, "project_name": "New Project",
            "controller_type": 1, "device_path": "",
            "device_index": 0, "adb_path": "127.0.0.1",
            "adb_port": 5555, "desktop_region": "",
            "duration_time": 200, "run_max_times": 200, "stop_hotkey": "Ctrl+Q",
            "tasks": []
        }

    # ============================================================
    #  UI 布局
    # ============================================================
    def _build_ui(self):
        menubar = tk.Menu(self.root)
        fmenu = tk.Menu(menubar, tearoff=0)
        fmenu.add_command(label="新建项目", command=self._new_project, accelerator="Ctrl+N")
        fmenu.add_command(label="打开 JSON", command=self._load_json, accelerator="Ctrl+O")
        fmenu.add_command(label="保存", command=self._save_json, accelerator="Ctrl+S")
        fmenu.add_command(label="另存为...", command=self._save_as_json)
        fmenu.add_separator()
        fmenu.add_command(label="导出 (ZIP)", command=self._export)
        fmenu.add_command(label="导入 (ZIP)", command=self._import)
        fmenu.add_separator()
        fmenu.add_command(label="运行", command=self._run, accelerator="F5")
        menubar.add_cascade(label="文件", menu=fmenu)
        self.root.config(menu=menubar)
        self.root.bind("<Control-n>", lambda e: self._new_project())
        self.root.bind("<Control-o>", lambda e: self._load_json())
        self.root.bind("<Control-s>", lambda e: self._save_json())
        self.root.bind("<F5>", lambda e: self._run())

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned, width=200)
        paned.add(left, weight=0)
        self._build_file_list(left)

        mid = ttk.Frame(paned, width=250)
        paned.add(mid, weight=0)
        self._build_settings(mid)

        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self._build_workflow(right)

        self.status = ttk.Label(self.root, text="就绪 | Ctrl+N 新建  Ctrl+S 保存  F5 运行",
                                relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_file_list(self, parent):
        ttk.Label(parent, text="项目文件", font=("", 10, "bold")).pack(pady=(5,0))

        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Entry(dir_frame, textvariable=self._project_root, width=18).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="..", width=3, command=self._browse_root).pack(side=tk.RIGHT)

        self.file_list = tk.Listbox(parent, height=12, exportselection=False)
        self.file_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.file_list.bind("<<ListboxSelect>>", self._on_select)

        btn = ttk.Frame(parent)
        btn.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(btn, text="新建", command=self._new_project).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn, text="刷新", command=self._refresh_file_list).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn, text="删除", command=self._delete_file).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_settings(self, parent):
        ttk.Label(parent, text="项目设置", font=("", 10, "bold")).pack(pady=(5,0))
        f = ttk.Frame(parent, padding=5)
        f.pack(fill=tk.X)

        self.sv_name = tk.StringVar(value=self.data["project_name"])
        self.sv_type = tk.StringVar(value="桌面")
        self.sv_window = tk.StringVar(value=self.data["device_path"])
        self.sv_region = tk.StringVar(value=self.data["desktop_region"])
        self.sv_duration = tk.StringVar(value=str(self.data["duration_time"]))
        self.sv_max_times = tk.StringVar(value=str(self.data["run_max_times"]))

        def row(label, var, row_idx):
            ttk.Label(f, text=label).grid(row=row_idx, column=0, sticky=tk.W, pady=2)
            e = ttk.Entry(f, textvariable=var, width=22)
            e.grid(row=row_idx, column=1, sticky=tk.EW, pady=2, padx=(5,0))

        row("项目名称:", self.sv_name, 0)
        ttk.Label(f, text="控制器:").grid(row=1, column=0, sticky=tk.W)
        cb = ttk.Combobox(f, textvariable=self.sv_type, values=["桌面","ADB"], width=20, state="readonly")
        cb.grid(row=1, column=1, sticky=tk.EW, padx=(5,0))
        row("窗口标题:", self.sv_window, 2)
        row("裁剪区域:", self.sv_region, 3)
        ttk.Label(f, text="x,y,w,h", font=("", 7)).grid(row=3, column=2, sticky=tk.W)
        row("间隔(ms):", self.sv_duration, 4)
        row("最大循环:", self.sv_max_times, 5)
        f.columnconfigure(1, weight=1)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Button(parent, text="+ 添加任务", command=self._add_task).pack(pady=2, fill=tk.X, padx=5)
        ttk.Button(parent, text="运行 (F5)", command=self._run).pack(pady=2, fill=tk.X, padx=5)
        self._stop_btn = ttk.Button(parent, text="■ 停止运行", command=self._stop_engine, state=tk.DISABLED)
        self._stop_btn.pack(pady=2, fill=tk.X, padx=5)

    def _build_workflow(self, parent):
        hint = ttk.Label(parent, text="ℹ Block=循环体(内部指令按序匹配,命中执行) | Block间顺序执行",
                         font=("", 8), foreground="gray")
        hint.pack(pady=(0,2))

        bar = ttk.Frame(parent)
        bar.pack(fill=tk.X, pady=(5,0))
        for text, cmd in [("+ 循环", self._add_loop_group), ("+ Block", self._add_block), ("+ 指令", self._add_code),
                           ("模板", self._show_templates),
                           ("存模板", self._save_as_template),
                           ("编辑", self._edit_node), ("删除", self._delete_node),
                           ("↑", lambda: self._move(-1)), ("↓", lambda: self._move(1))]:
            ttk.Button(bar, text=text, command=cmd, width=6).pack(side=tk.LEFT, padx=1)

        self.tree = ttk.Treeview(parent, selectmode="browse", show="tree headings",
                                  columns=("info",), height=22)
        self.tree.heading("#0", text="工作流节点")
        self.tree.heading("info", text="详情")
        self.tree.column("#0", width=240)
        self.tree.column("info", width=480)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tree.bind("<Double-1>", lambda e: self._edit_node())

    # ============================================================
    #  文件管理
    # ============================================================
    def _res_dir(self):
        d = os.path.join(self._project_root.get(), "res")
        os.makedirs(d, exist_ok=True)
        return d

    def _browse_root(self):
        d = filedialog.askdirectory(title="选择项目根目录")
        if d:
            self._project_root.set(d)
            self._refresh_file_list()

    def _refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        d = self._res_dir()
        if not os.path.isdir(d): return
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                self.file_list.insert(tk.END, f)

    def _on_select(self, evt):
        sel = self.file_list.curselection()
        if not sel: return
        fname = self.file_list.get(sel[0])
        path = os.path.join(self._res_dir(), fname)
        self._load_json_file(path)
        self._current_file = path

    def _delete_file(self):
        sel = self.file_list.curselection()
        if not sel: return
        fname = self.file_list.get(sel[0])
        path = os.path.join(self._res_dir(), fname)
        if messagebox.askyesno("删除", f"删除 {fname}?"):
            os.remove(path)
            self._refresh_file_list()
            if self._current_file == path:
                self._clear()

    def _clear(self):
        self.data = self._default_project()
        self._current_file = None
        self._refresh_all()

    def _new_project(self):
        name = simpledialog.askstring("新建项目", "项目名称:", parent=self.root)
        if not name: return
        # 创建 res/xx.json 和 data/xx/
        json_path = os.path.join(self._res_dir(), f"{name}.json")
        data_dir = os.path.join(self._project_root.get(), "data", name)
        os.makedirs(data_dir, exist_ok=True)

        self.data = self._default_project()
        self.data["project_name"] = name
        self._write_json(json_path)
        self._current_file = json_path
        self._refresh_all()

    def _load_json(self):
        path = filedialog.askopenfilename(initialdir=self._res_dir(),
                                           filetypes=[("JSON 文件", "*.json")])
        if path:
            self._project_root.set(os.path.dirname(os.path.dirname(path)))
            self._load_json_file(path)
            self._current_file = path
            self._refresh_file_list()

    def _load_json_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            # 向后兼容: 旧格式 blocks → loop_groups
            for task in self.data.get("tasks", []):
                if task.get("blocks") and not task.get("loop_groups"):
                    task["loop_groups"] = [{
                        "loop_id": 1, "loop_name": "Loop 1", "loop_count": 1,
                        "stop_condition_type": 0, "stop_image_path": "",
                        "stop_threshold": 0.9, "stop_text": "", "stop_time_out": 0,
                        "blocks": task.pop("blocks")
                    }]
            self._ui_from_data()
            self._refresh_tree()
        except Exception as e:
            messagebox.showerror("加载失败", str(e))

    def _save_json(self, evt=None):
        if self._current_file and os.path.exists(os.path.dirname(self._current_file)):
            self._sync_from_ui()
            self._write_json(self._current_file)
        else:
            self._save_as_json()

    def _save_as_json(self):
        self._sync_from_ui()
        path = filedialog.asksaveasfilename(
            initialdir=self._res_dir(), defaultextension=".json",
            initialfile=f"{self.data['project_name']}.json",
            filetypes=[("JSON 文件", "*.json")])
        if path:
            self._write_json(path)
            self._current_file = path
            self._refresh_file_list()

    def _write_json(self, path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.status.config(text=f"已保存: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _auto_save(self):
        """如果已有当前文件，自动保存"""
        if self._current_file:
            self._sync_from_ui()
            try:
                self._write_json(self._current_file)
            except:
                pass

    # ============================================================
    #  导出 / 导入
    # ============================================================
    def _export(self):
        self._sync_from_ui()
        name = self.data["project_name"]
        path = filedialog.asksaveasfilename(
            initialfile=f"{name}.zip", defaultextension=".zip",
            filetypes=[("ZIP 压缩包", "*.zip")])
        if not path: return

        root = self._project_root.get()
        json_file = os.path.join(root, "res", f"{name}.json")
        data_dir = os.path.join(root, "data", name)

        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 确保 JSON 已保存
                if not os.path.exists(json_file):
                    self._write_json(json_file)
                zf.write(json_file, f"res/{name}.json")

                # 打包图片目录
                if os.path.isdir(data_dir):
                    for f in os.listdir(data_dir):
                        fp = os.path.join(data_dir, f)
                        if os.path.isfile(fp):
                            zf.write(fp, f"data/{name}/{f}")

            self.status.config(text=f"已导出: {os.path.basename(path)}")
            messagebox.showinfo("导出成功", f"已导出:\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[("ZIP 压缩包", "*.zip")])
        if not path: return
        root = self._project_root.get()
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for member in zf.namelist():
                    target = os.path.join(root, member)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())

            self._refresh_file_list()
            # 尝试自动加载导入的 JSON
            for member in zf.namelist():
                if member.endswith(".json"):
                    json_path = os.path.join(root, member)
                    if os.path.exists(json_path):
                        self._load_json_file(json_path)
                        self._current_file = json_path
                        break

            messagebox.showinfo("导入成功", f"已导入到:\n{root}")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    # ============================================================
    #  同步与刷新
    # ============================================================
    def _refresh_all(self):
        self._ui_from_data()
        self._refresh_tree()
        self._refresh_file_list()

    def _ui_from_data(self):
        self.sv_name.set(self.data.get("project_name", ""))
        self.sv_type.set("桌面" if self.data.get("controller_type", 0) == 1 else "ADB")
        self.sv_window.set(self.data.get("device_path", ""))
        self.sv_region.set(self.data.get("desktop_region", ""))
        self.sv_duration.set(str(self.data.get("duration_time", 200)))
        self.sv_max_times.set(str(self.data.get("run_max_times", 200)))

    def _sync_from_ui(self):
        self.data["project_name"] = self.sv_name.get()
        self.data["controller_type"] = 1 if self.sv_type.get() == "桌面" else 0
        self.data["device_path"] = self.sv_window.get()
        self.data["desktop_region"] = self.sv_region.get()
        try: self.data["duration_time"] = int(self.sv_duration.get())
        except: pass
        try: self.data["run_max_times"] = int(self.sv_max_times.get())
        except: pass

    COND = {0:"无条件", 1:"匹配图片", 2:"文字识别", 3:"超时"}
    ACT = {0:"空", 1:"点击", 2:"滑动", 3:"长按", 4:"按键", 5:"等待", 6:"退出循环", 7:"退出任务", 8:"退出"}

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for t_idx, task in enumerate(self.data.get("tasks", [])):
            t_id = self.tree.insert("", tk.END, text=f"📋 {task['task_name']}", values=("",))
            for lg_idx, lg in enumerate(task.get("loop_groups", [])):
                cnt = lg.get("loop_count", 1)
                st = "" if lg.get("stop_condition_type", 0) == 0 else "条件停"
                label = f"🔁 {lg['loop_name']} (x{cnt} {st})" if st else f"🔁 {lg['loop_name']} (x{cnt})"
                lg_id = self.tree.insert(t_id, tk.END, text=label, values=("",))
                for b_idx, block in enumerate(lg.get("blocks", [])):
                    b_id = self.tree.insert(lg_id, tk.END, text=f"🔄 {block['block_name']}", values=("",))
                    for c_idx, code in enumerate(block.get("codes", [])):
                        info = self._summary(code)
                        self.tree.insert(b_id, tk.END, text=f"▸ 指令{c_idx+1}", values=(info,))
        self._expand_all()
        tc = sum(len(b.get('codes',[])) for t in self.data.get('tasks',[]) for lg in t.get('loop_groups',[]) for b in lg.get('blocks',[]))
        nc = sum(1 for t in self.data.get('tasks',[]) for lg in t.get('loop_groups',[]))
        nb = sum(len(lg.get('blocks',[])) for t in self.data.get('tasks',[]) for lg in t.get('loop_groups',[]))
        self.status.config(text=f"任务:{len(self.data.get('tasks',[]))} | 循环:{nc} | Block:{nb} | 指令:{tc}")
    def _expand_all(self):
        def go(item):
            self.tree.item(item, open=True)
            for c in self.tree.get_children(item):
                go(c)
        for item in self.tree.get_children():
            go(item)

    def _summary(self, code):
        cond = self.COND.get(code.get("first_value", 0), "?")
        act = self.ACT.get(code.get("second_value", 0), "?")
        e = []
        if code.get("image_path"): e.append(f"模板:{code['image_path']}")
        if code.get("sleep_time", 0) > 0: e.append(f"{code['sleep_time']}ms")
        if code.get("second_value") == 1: e.append(f"偏移({code.get('click_x',0)},{code.get('click_y',0)})")
        return f"条件:{cond} → 动作:{act}" + (" | " + " ".join(e) if e else "")

    def _sel(self):
        s = self.tree.selection()
        if not s: return None, None, None, None
        i = s[0]
        p = self.tree.parent(i)
        gp = self.tree.parent(p) if p else ""
        ggp = self.tree.parent(gp) if gp else ""
        return i, p, gp, ggp

    def _tk_idx(self, item, txt, parent, grandparent, great_grandparent=None):
        if txt.startswith("📋"): return self.tree.index(item)
        if txt.startswith("🔁"): return self.tree.index(parent)
        if txt.startswith("🔄"): return self.tree.index(grandparent)
        if txt.startswith("▸"): return self.tree.index(great_grandparent)
        return None

    # ============================================================
    #  节点 CRUD
    # ============================================================
    def _add_task(self):
        name = simpledialog.askstring("新建任务", "名称:", parent=self.root)
        if name:
            self._sync_from_ui()
            self.data.setdefault("tasks", []).append(
                {"task_id": len(self.data["tasks"])+1, "task_name": name,
                 "loop_groups": [{"loop_id": 1, "loop_name": "Loop 1", "loop_count": 1,
                                   "stop_condition_type": 0, "stop_image_path": "",
                                   "stop_threshold": 0.9, "stop_text": "",
                                   "stop_time_out": 0, "blocks": []}]})
            self._refresh_tree()

    def _add_loop_group(self):
        item, parent, grandparent, _ = self._sel()
        if not item: return
        txt = self.tree.item(item, "text")
        self._sync_from_ui()
        t_idx = self._tk_idx(item, txt, parent, grandparent)
        if t_idx is None: return
        lg = self._loop_group_dialog(None)
        if lg:
            self.data["tasks"][t_idx].setdefault("loop_groups", []).append(lg)
            self._refresh_tree()
            self._auto_save()

    def _loop_group_dialog(self, existing):
        dlg = tk.Toplevel(self.root)
        dlg.title("编辑循环组" if existing else "新建循环组")
        dlg.geometry("480x380")
        dlg.resizable(False, False)
        default = {"loop_id": 1, "loop_name": "Loop 1", "loop_count": 1,
                    "stop_condition_type": 0, "stop_image_path": "",
                    "stop_threshold": 0.9, "stop_text": "", "stop_time_out": 0}
        vals = {**default, **existing} if existing else default
        vars_ = {k: tk.StringVar(value=str(v)) for k, v in vals.items()}
        result = [None]
        f = ttk.Frame(dlg, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        def mk(lbl, key, r, w=10):
            ttk.Label(f, text=lbl).grid(row=r, column=0, sticky=tk.W, pady=3)
            ttk.Entry(f, textvariable=vars_[key], width=w).grid(row=r, column=1, sticky=tk.W, padx=(5,0))
        mk("循环名称:", "loop_name", 0, 15)
        mk("循环次数 (0=无限):", "loop_count", 1, 6)
        ttk.Separator(f, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)
        ttk.Label(f, text="停止条件:", font=("", 10, "bold")).grid(row=3, column=0, sticky=tk.W)
        cb = ttk.Combobox(f, textvariable=vars_["stop_condition_type"],
                          values=["0-仅靠次数","1-匹配图片","2-文字识别","3-超时"],
                          width=14, state="readonly")
        cb.grid(row=3, column=1, sticky=tk.W, padx=(5,0))
        st = vals["stop_condition_type"]
        st_labels = {0:"仅靠次数",1:"匹配图片",2:"文字识别",3:"超时"}
        cb.set(f"{st}-{st_labels[st]}")
        mk("图片路径:", "stop_image_path", 4, 18)
        mk("匹配阈值:", "stop_threshold", 5, 6)
        mk("识别文字:", "stop_text", 6, 18)
        mk("超时(ms):", "stop_time_out", 7, 8)
        def save():
            try:
                result[0] = {
                    "loop_id": existing.get("loop_id", 1) if existing else 1,
                    "loop_name": vars_["loop_name"].get(),
                    "loop_count": int(vars_["loop_count"].get()),
                    "stop_condition_type": int(vars_["stop_condition_type"].get().split("-")[0]),
                    "stop_image_path": vars_["stop_image_path"].get().strip(),
                    "stop_threshold": float(vars_["stop_threshold"].get()),
                    "stop_text": vars_["stop_text"].get().strip(),
                    "stop_time_out": int(vars_["stop_time_out"].get()),
                    "blocks": existing.get("blocks", []) if existing else [],
                }
                dlg.destroy()
            except ValueError as e:
                messagebox.showerror("输入错误", str(e), parent=dlg)
        ttk.Button(f, text="确定", command=save).grid(row=8, column=0, columnspan=2, pady=15)
        dlg.transient(self.root)
        dlg.grab_set()
        self.root.wait_window(dlg)
        return result[0]

    def _init_default_templates(self):
        """首次运行时创建默认模板"""
        tdir = self._template_dir()
        defaults = {
            "匹配点击跳出": [
                {"code_id":1,"first_value":1,"second_value":1,"image_path":"","threshold":0.9,"click_x":0,"click_y":0,"sleep_time":0,"key_code":0,"swipe_x_1":0,"swipe_y_1":0,"swipe_x_2":0,"swipe_y_2":0,"swipe_time":300,"text":"","time_out":0},{"code_id":1,"first_value":0,"second_value":5,"image_path":"","threshold":0.9,"click_x":0,"click_y":0,"sleep_time":300,"key_code":0,"swipe_x_1":0,"swipe_y_1":0,"swipe_x_2":0,"swipe_y_2":0,"swipe_time":300,"text":"","time_out":0},{"code_id":1,"first_value":1,"second_value":6,"image_path":"","threshold":0.9,"click_x":0,"click_y":0,"sleep_time":0,"key_code":0,"swipe_x_1":0,"swipe_y_1":0,"swipe_x_2":0,"swipe_y_2":0,"swipe_time":300,"text":"","time_out":0},
            ],
            "简单点击": [
                {"first_value":1,"second_value":1,"image_path":"","threshold":0.9,"comment":"匹配到目标->点击"},
            ],
            "等待并退出": [
                {"first_value":1,"second_value":6,"image_path":"","threshold":0.95,"comment":"匹配到目标->退出循环"},
            ],
        }
        for name, codes in defaults.items():
            path = os.path.join(tdir, f"{name}.json")
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"name": name, "codes": codes}, f, indent=2, ensure_ascii=False)

    def _template_dir(self):
        d = os.path.join(self._project_root.get(), "template")
        os.makedirs(d, exist_ok=True)
        return d

    def _save_as_template(self):
        """保存选中 Block 为模板"""
        item, parent, grandparent, ggp = self._sel()
        if not item: return
        txt = self.tree.item(item, "text")
        if not txt.startswith("🔄"): return
        self._sync_from_ui()
        t_idx = self.tree.index(grandparent)
        lg_idx = self.tree.index(parent)
        b_idx = self.tree.index(item)
        block = self.data["tasks"][t_idx]["loop_groups"][lg_idx]["blocks"][b_idx]
        name = simpledialog.askstring("存为模板", "模板名称:", parent=self.root)
        if not name: return
        path = os.path.join(self._template_dir(), f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"name": name, "codes": block.get("codes", [])}, f, indent=2, ensure_ascii=False)
        self.status.config(text=f"模板已保存: {name}")

    def _show_templates(self):
        """弹出模板浏览窗口，可选择导入"""
        tdir = self._template_dir()
        templates = [f for f in sorted(os.listdir(tdir)) if f.endswith(".json")]

        dlg = tk.Toplevel(self.root)
        dlg.title("模板列表")
        dlg.geometry("350x400")
        dlg.resizable(False, False)

        ttk.Label(dlg, text="模板列表 (template/)", font=("", 10, "bold")).pack(pady=(10,5))

        lb = tk.Listbox(dlg, height=14)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for t in templates:
            lb.insert(tk.END, t.replace(".json", ""))

        btn = ttk.Frame(dlg)
        btn.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn, text="导入", command=lambda: self._import_template(lb, dlg)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="重命名", command=lambda: self._rename_template(lb)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="删除", command=lambda: self._delete_template(lb)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="取消", command=dlg.destroy).pack(side=tk.RIGHT, padx=2)

        dlg.transient(self.root)
        dlg.grab_set()

    def _import_template(self, lb, dlg):
        sel = lb.curselection()
        if not sel: return
        name = lb.get(sel[0])
        path = os.path.join(self._template_dir(), f"{name}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                tmpl = json.load(f)
        except:
            return
        # 找到当前选中位置插入
        item, parent, grandparent, ggp = self._sel()
        if not item: return
        txt = self.tree.item(item, "text")
        t_idx = self._tk_idx(item, txt, parent, grandparent, ggp)
        if t_idx is None: return
        self._sync_from_ui()
        lgs = self.data["tasks"][t_idx].setdefault("loop_groups", [])
        if not lgs:
            lgs.append({"loop_id":1,"loop_name":"Loop 1","loop_count":1,"stop_condition_type":0,"stop_image_path":"","stop_threshold":0.9,"stop_text":"","stop_time_out":0,"blocks":[]})
        blocks = lgs[-1].setdefault("blocks", [])
        block_name = tmpl.get("name", name)
        blocks.append({"block_id": len(blocks)+1, "block_name": block_name, "codes": tmpl.get("codes", [])})
        self._refresh_tree()
        self._auto_save()
        dlg.destroy()
        self.status.config(text=f"已导入模板: {block_name}")

    def _rename_template(self, lb):
        sel = lb.curselection()
        if not sel: return
        old = lb.get(sel[0])
        new = simpledialog.askstring("重命名", "新名称:", initialvalue=old, parent=self.root)
        if new and new != old:
            src = os.path.join(self._template_dir(), f"{old}.json")
            dst = os.path.join(self._template_dir(), f"{new}.json")
            os.rename(src, dst)
            lb.delete(sel[0])
            lb.insert(sel[0], new)

    def _delete_template(self, lb):
        sel = lb.curselection()
        if not sel: return
        name = lb.get(sel[0])
        if messagebox.askyesno("删除模板", f"删除模板 {name}?", parent=self.root):
            os.remove(os.path.join(self._template_dir(), f"{name}.json"))
            lb.delete(sel[0])

    def _add_block(self):
        item, parent, grandparent, ggp = self._sel()
        if not item: return
        txt = self.tree.item(item, "text")
        self._sync_from_ui()
        t_idx = self._tk_idx(item, txt, parent, grandparent, ggp)
        if t_idx is None: return
        tasks = self.data.setdefault("tasks", [])
        if t_idx >= len(tasks): return
        lgs = tasks[t_idx].setdefault("loop_groups", [])
        if not lgs:
            lgs.append({"loop_id":1,"loop_name":"Loop 1","loop_count":1,"stop_condition_type":0,"stop_image_path":"","stop_threshold":0.9,"stop_text":"","stop_time_out":0,"blocks":[]})
        if txt.startswith("📋"):
            lg_idx = len(lgs) - 1
        elif txt.startswith("🔁"):
            lg_idx = self.tree.index(item)
        elif txt.startswith("🔄"):
            lg_idx = self.tree.index(parent)
        elif txt.startswith("▸"):
            lg_idx = self.tree.index(grandparent) if grandparent else (len(lgs) - 1)
        else:
            return
        if lg_idx < 0 or lg_idx >= len(lgs): return
        target = lgs[lg_idx]
        name = simpledialog.askstring("新建 Block", "名称:", parent=self.root)
        if name:
            target.setdefault("blocks", []).append({"block_id": len(target.get("blocks",[]))+1, "block_name": name, "codes": []})
            self._refresh_tree()
            self._auto_save()

    def _add_code(self):
        item, parent, grandparent, ggp = self._sel()
        if not item: return
        txt = self.tree.item(item, "text")
        self._sync_from_ui()
        t_idx = self._tk_idx(item, txt, parent, grandparent, ggp)
        if t_idx is None: return
        tasks = self.data.setdefault("tasks", [])
        if t_idx >= len(tasks): return
        lgs = tasks[t_idx].setdefault("loop_groups", [])
        if not lgs:
            lgs.append({"loop_id":1,"loop_name":"Loop 1","loop_count":1,"stop_condition_type":0,"stop_image_path":"","stop_threshold":0.9,"stop_text":"","stop_time_out":0,"blocks":[]})
        # 找到目标 LoopGroup
        if txt.startswith("📋"):
            lg_idx = len(lgs) - 1
        elif txt.startswith("🔁"):
            lg_idx = self.tree.index(item)
        elif txt.startswith("🔄"):
            lg_idx = self.tree.index(parent)
        elif txt.startswith("▸"):
            lg_idx = self.tree.index(grandparent) if grandparent else (len(lgs) - 1)
        else:
            return
        if lg_idx < 0 or lg_idx >= len(lgs): return
        blocks = lgs[lg_idx].setdefault("blocks", [])
        # 找到目标 Block (or create default)
        if txt.startswith("📋") or txt.startswith("🔁"):
            if not blocks:
                blocks.append({"block_id": 1, "block_name": "Block 1", "codes": []})
            target = blocks[-1]
        elif txt.startswith("🔄"):
            b_idx = self.tree.index(item)
            if b_idx < 0 or b_idx >= len(blocks): return
            target = blocks[b_idx]
        elif txt.startswith("▸"):
            b_idx = self.tree.index(parent)
            if b_idx < 0 or b_idx >= len(blocks): return
            target = blocks[b_idx]
        else:
            return
        code = self._code_dialog(None)
        if code:
            target.setdefault("codes", []).append(code)
            self._refresh_tree()
            self._auto_save()

    def _edit_node(self):
        try:
            item, parent, grandparent, ggp = self._sel()
            if not item: return
            txt = self.tree.item(item, "text")
            self._sync_from_ui()
            if txt.startswith("📋"):
                t_idx = self.tree.index(item)
                task = self.data["tasks"][t_idx]
                n = simpledialog.askstring("编辑任务", "名称:", initialvalue=task["task_name"], parent=self.root)
                if n: task["task_name"] = n; self._refresh_tree()
                self._auto_save()
            elif txt.startswith("🔁"):
                t_idx = self.tree.index(parent)
                lg_idx = self.tree.index(item)
                lg = self.data["tasks"][t_idx]["loop_groups"][lg_idx]
                nlg = self._loop_group_dialog(lg)
                if nlg:
                    nlg["blocks"] = lg.get("blocks", [])
                    self.data["tasks"][t_idx]["loop_groups"][lg_idx] = nlg
                    self._refresh_tree()
                    self._auto_save()
            elif txt.startswith("🔄"):
                t_idx = self.tree.index(grandparent)
                lg_idx = self.tree.index(parent)
                b_idx = self.tree.index(item)
                block = self.data["tasks"][t_idx]["loop_groups"][lg_idx]["blocks"][b_idx]
                n = simpledialog.askstring("编辑 Block", "名称:", initialvalue=block["block_name"], parent=self.root)
                if n: block["block_name"] = n; self._refresh_tree()
                self._auto_save()
            elif txt.startswith("▸"):
                t_idx = self._tk_idx(item, txt, parent, grandparent, ggp)
                lg_idx = self.tree.index(grandparent)
                b_idx = self.tree.index(parent)
                c_idx = self.tree.index(item)
                code = self.data["tasks"][t_idx]["loop_groups"][lg_idx]["blocks"][b_idx]["codes"][c_idx]
                nc = self._code_dialog(code)
                if nc:
                    self.data["tasks"][t_idx]["loop_groups"][lg_idx]["blocks"][b_idx]["codes"][c_idx] = nc
                    self._refresh_tree()
                    self._auto_save()
        except (IndexError, KeyError):
            pass

    def _delete_node(self):
        try:
            item, parent, grandparent, ggp = self._sel()
            if not item: return
            txt = self.tree.item(item, "text")
            self._sync_from_ui()
            if txt.startswith("📋"):
                del self.data["tasks"][self.tree.index(item)]
            elif txt.startswith("🔁"):
                del self.data["tasks"][self.tree.index(parent)]["loop_groups"][self.tree.index(item)]
            elif txt.startswith("🔄"):
                del self.data["tasks"][self.tree.index(grandparent)]["loop_groups"][self.tree.index(parent)]["blocks"][self.tree.index(item)]
            elif txt.startswith("▸"):
                del self.data["tasks"][self.tree.index(ggp)]["loop_groups"][self.tree.index(grandparent)]["blocks"][self.tree.index(parent)]["codes"][self.tree.index(item)]
            self._refresh_tree()
            self._auto_save()
        except (IndexError, KeyError):
            pass

    def _move(self, d):
        item, parent, grandparent, ggp = self._sel()
        if not item: return
        txt = self.tree.item(item, "text")
        self._sync_from_ui()
        try:
            if txt.startswith("📋"):
                lst, idx = self.data["tasks"], self.tree.index(item)
            elif txt.startswith("🔁"):
                lst = self.data["tasks"][self.tree.index(parent)]["loop_groups"]; idx = self.tree.index(item)
            elif txt.startswith("🔄"):
                lst = self.data["tasks"][self.tree.index(grandparent)]["loop_groups"][self.tree.index(parent)]["blocks"]; idx = self.tree.index(item)
            elif txt.startswith("▸"):
                lst = self.data["tasks"][self.tree.index(ggp)]["loop_groups"][self.tree.index(grandparent)]["blocks"][self.tree.index(parent)]["codes"]; idx = self.tree.index(item)
            else: return
            ni = idx + d
            if 0 <= ni < len(lst): lst[idx], lst[ni] = lst[ni], lst[idx]
            self._refresh_tree()
            self._auto_save()
        except: pass

    # ============================================================
    #  指令编辑弹窗 (浏览图片 / 截图)
    # ============================================================
    def _code_dialog(self, existing):
        dlg = tk.Toplevel(self.root)
        dlg.title("编辑指令" if existing else "新建指令")
        dlg.geometry("700x580")
        dlg.resizable(False, False)

        # 默认值补全所有字段
        default_vals = {"first_value": 1, "second_value": 1, "image_path": "",
                        "threshold": 0.9, "click_x": 0, "click_y": 0, "click_x_max": 0, "click_y_max": 0,
                        "sleep_time": 0, "sleep_time_max": 0, "key_code": 0,
                        "swipe_x_1": 0, "swipe_y_1": 0, "swipe_x_2": 0, "swipe_y_2": 0, "swipe_x_1_max": 0, "swipe_y_1_max": 0, "swipe_x_2_max": 0, "swipe_y_2_max": 0,
                        "swipe_time": 300, "swipe_time_max": 0, "text": "", "time_out": 0}
        vals = {**default_vals, **existing} if existing else default_vals
        vars_ = {k: tk.StringVar(value=str(v)) for k, v in vals.items()}
        result = [None]

        # 水平分割: 左侧表单 + 右侧预览
        main = ttk.Frame(dlg, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        f = ttk.Frame(main)
        f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- 右侧预览面板 ---
        preview_frame = ttk.LabelFrame(main, text="模板预览", width=210, height=220)
        preview_frame.pack(side=tk.RIGHT, fill=tk.NONE, padx=(10, 0))
        preview_frame.pack_propagate(False)
        preview_label = ttk.Label(preview_frame, text="选择图片后可预览",
                                  anchor=tk.CENTER, background="#e0e0e0")
        preview_label.pack(fill=tk.BOTH, expand=True)

        def refresh_preview(path):
            """根据图片路径刷新右侧预览图"""
            if not path:
                preview_label.config(image="", text="选择图片后可预览",
                                    background="#e0e0e0")
                return
            full = os.path.join(self._project_root.get(), path)
            if not os.path.isfile(full):
                preview_label.config(image="", text=f"文件不存在:\n{path}",
                                    background="#e0e0e0")
                return
            try:
                from PIL import Image, ImageTk
            except ImportError:
                preview_label.config(image="", text="需安装 Pillow:\npip install Pillow",
                                    background="#e0e0e0")
                return
            try:
                img = Image.open(full)
                img.thumbnail((190, 190), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                preview_label.config(image=photo, text="", background="white")
                preview_label.image = photo
            except Exception as e:
                preview_label.config(image="", text=f"加载失败:\n{str(e)[:40]}",
                                    background="#e0e0e0")

        vars_["image_path"].trace_add("write",
            lambda *_, p=vars_["image_path"]: refresh_preview(p.get()))

        ttk.Label(f, text="触发条件:", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        cb1 = ttk.Combobox(f, textvariable=vars_["first_value"],
                            values=["0-无条件","1-匹配图片","2-文字识别","3-超时"], width=18, state="readonly")
        cb1.grid(row=0, column=1, sticky=tk.EW, pady=2)
        fv = vals["first_value"]; cb1.set(f"{fv}-{self.COND.get(fv,'?')}")

        ttk.Label(f, text="执行动作:", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W)
        cb2 = ttk.Combobox(f, textvariable=vars_["second_value"],
                            values=["0-空","1-点击","2-滑动","3-长按","4-按键",
                                    "5-等待","6-退出循环","7-退出任务","8-退出程序"], width=18, state="readonly")
        cb2.grid(row=1, column=1, sticky=tk.EW, pady=2)
        sv = vals["second_value"]; cb2.set(f"{sv}-{self.ACT.get(sv,'?')}")

        tip_frame = ttk.Frame(f)
        tip_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=3)
        ttk.Label(tip_frame, text="提示: 在Block末尾加 [匹配目标 → 退出循环] 即可跳转下一Block",
                  font=("", 8), foreground="gray").pack()

        ttk.Separator(f, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=5)

        # --- 条件参数 (动态) ---
        cond_frame = ttk.LabelFrame(f, text="条件参数", padding=5)
        cond_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=3)

        # --- 动作参数 (动态) ---
        act_frame = ttk.LabelFrame(f, text="动作参数", padding=5)
        act_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=3)

        def _mk_field(parent, label, var_name, row, width=8):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
            e = ttk.Entry(parent, textvariable=vars_[var_name], width=width)
            e.grid(row=row, column=1, sticky=tk.W, pady=2, padx=(5,0))

        def _mk_browse(parent, row):
            frm = ttk.Frame(parent)
            frm.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=2)
            ttk.Label(frm, text="模板图片:").pack(side=tk.LEFT)
            ttk.Entry(frm, textvariable=vars_["image_path"], width=18).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            ttk.Button(frm, text="浏览", width=5,
                       command=lambda: self._browse_image(vars_["image_path"])).pack(side=tk.LEFT)
            ttk.Button(frm, text="截图", width=5,
                       command=lambda: self._capture_image(vars_["image_path"], dlg)).pack(side=tk.LEFT, padx=2)

        def update_cond(*_):
            for w in cond_frame.winfo_children():
                w.destroy()
            try:
                cv = int(vars_["first_value"].get().split("-")[0])
            except:
                cv = 1
            if cv == 1:
                _mk_browse(cond_frame, 0)
                _mk_field(cond_frame, "匹配阈值:", "threshold", 1, 6)
                refresh_preview(vars_["image_path"].get())
            elif cv == 2:
                _mk_field(cond_frame, "识别文字:", "text", 0, 18)
                preview_label.config(image="", text="文字识别模式\n(无需模板图片)", background="#e0e0e0")
            elif cv == 3:
                _mk_field(cond_frame, "超时(ms):", "time_out", 0, 8)
                preview_label.config(image="", text="超时模式\n(无需模板图片)", background="#e0e0e0")
            else:
                ttk.Label(cond_frame, text="无需额外参数", foreground="gray").grid(row=0, column=0, sticky=tk.W, pady=3)

        def update_act(*_):
            for w in act_frame.winfo_children():
                w.destroy()
            try:
                av = int(vars_["second_value"].get().split("-")[0])
            except:
                av = 1
            if av == 1:
                _mk_field(act_frame, "偏移 X:", "click_x", 0)
                _mk_field(act_frame, "偏移 Y:", "click_y", 1)
                _mk_field(act_frame, "随机上限 X:", "click_x_max", 2)
                _mk_field(act_frame, "随机上限 Y:", "click_y_max", 3)
            elif av == 2:
                _mk_field(act_frame, "起点 X:", "swipe_x_1", 0)
                _mk_field(act_frame, "起点 Y:", "swipe_y_1", 1)
                _mk_field(act_frame, "终点 X:", "swipe_x_2", 2)
                _mk_field(act_frame, "终点 Y:", "swipe_y_2", 3)
                _mk_field(act_frame, "起点X上限:", "swipe_x_1_max", 4)
                _mk_field(act_frame, "起点Y上限:", "swipe_y_1_max", 5)
                _mk_field(act_frame, "终点X上限:", "swipe_x_2_max", 6)
                _mk_field(act_frame, "终点Y上限:", "swipe_y_2_max", 7)
                _mk_field(act_frame, "滑动时长(ms):", "swipe_time", 8)
                _mk_field(act_frame, "时长上限(ms):", "swipe_time_max", 9)
            elif av == 3:
                _mk_field(act_frame, "偏移 X:", "click_x", 0)
                _mk_field(act_frame, "偏移 Y:", "click_y", 1)
                _mk_field(act_frame, "随机上限 X:", "click_x_max", 2)
                _mk_field(act_frame, "随机上限 Y:", "click_y_max", 3)
                _mk_field(act_frame, "长按(ms):", "sleep_time", 4)
                _mk_field(act_frame, "时长上限(ms):", "sleep_time_max", 5)
            elif av == 4:
                _mk_field(act_frame, "按键代码:", "key_code", 0)
            elif av == 5:
                _mk_field(act_frame, "等待(ms):", "sleep_time", 0)
                _mk_field(act_frame, "随机上限(ms):", "sleep_time_max", 1)
            else:
                ttk.Label(act_frame, text="无需额外参数", foreground="gray").grid(row=0, column=0, sticky=tk.W, pady=3)

        vars_["first_value"].trace_add("write", lambda *_: update_cond())
        vars_["second_value"].trace_add("write", lambda *_: update_act())

        update_cond()
        update_act()

        def save():
            try:
                code = {
                    "code_id": existing.get("code_id", 1) if existing else 1,
                    "first_value": int(vars_["first_value"].get().split("-")[0]),
                    "second_value": int(vars_["second_value"].get().split("-")[0]),
                    "image_path": vars_["image_path"].get().strip(),
                    "threshold": float(vars_["threshold"].get()),
                    "click_x": int(vars_["click_x"].get()),
                    "click_y": int(vars_["click_y"].get()),
                    "click_x_max": int(vars_["click_x_max"].get()),
                    "click_y_max": int(vars_["click_y_max"].get()),
                    "sleep_time": int(vars_["sleep_time"].get()),
                    "sleep_time_max": int(vars_["sleep_time_max"].get()),
                    "key_code": int(vars_["key_code"].get()),
                    "swipe_x_1": int(vars_["swipe_x_1"].get()),
                    "swipe_y_1": int(vars_["swipe_y_1"].get()),
                    "swipe_x_2": int(vars_["swipe_x_2"].get()),
                    "swipe_y_2": int(vars_["swipe_y_2"].get()),
                    "swipe_x_1_max": int(vars_["swipe_x_1_max"].get()),
                    "swipe_y_1_max": int(vars_["swipe_y_1_max"].get()),
                    "swipe_x_2_max": int(vars_["swipe_x_2_max"].get()),
                    "swipe_y_2_max": int(vars_["swipe_y_2_max"].get()),
                    "swipe_time": int(vars_["swipe_time"].get()),
                    "swipe_time_max": int(vars_["swipe_time_max"].get()),
                    "text": vars_["text"].get().strip(),
                    "time_out": int(vars_["time_out"].get()),
                }
                result[0] = code
                dlg.destroy()
            except ValueError as e:
                messagebox.showerror("输入错误", str(e), parent=dlg)

        ttk.Button(f, text="确定", command=save).grid(row=5, column=0, columnspan=3, pady=15)
        f.columnconfigure(1, weight=1)

        refresh_preview(vars_["image_path"].get())

        dlg.transient(self.root)
        dlg.grab_set()
        self.root.wait_window(dlg)
        return result[0]


    def _browse_image(self, sv):
        path = filedialog.askopenfilename(
            filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp"), ("所有", "*.*")])
        if not path: return
        os.makedirs(self._data_dir, exist_ok=True)
        dst = os.path.join(self._data_dir, os.path.basename(path))
        if path != dst:
            shutil.copy2(path, dst)
        root = self._project_root.get()
        sv.set(os.path.relpath(dst, root).replace("\\", "/"))

    def _capture_image(self, sv, dlg):
        mode = messagebox.askyesnocancel("截图", "是 = 全屏截图\n否 = 框选区域\n取消 = 不截图", parent=dlg)
        if mode is None: return

        import numpy as np
        if mode:
            try:
                import mss
                with mss.mss() as sct:
                    img = np.array(sct.grab(sct.monitors[1]))[:, :, :3]
            except ImportError:
                import pyautogui
                img = pyautogui.screenshot()
                img = np.array(img)[:, :, ::-1]
        else:
            dlg.iconify()
            try:
                from openar.desktop_controller import DesktopController
                region = DesktopController.select_region()
            finally:
                dlg.deiconify(); dlg.lift()
            if not region: return
            try:
                import mss
                with mss.mss() as sct:
                    mon = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
                    img = np.array(sct.grab(mon))[:, :, :3]
            except ImportError:
                import pyautogui
                img = pyautogui.screenshot(region=region)
                img = np.array(img)[:, :, ::-1]

        os.makedirs(self._data_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(self._data_dir, f"capture_{ts}.png")
        import cv2
        cv2.imwrite(dst, img)
        root = self._project_root.get()
        sv.set(os.path.relpath(dst, root).replace("\\", "/"))
        messagebox.showinfo("截图成功", f"已保存:\n{dst}", parent=dlg)

    # ============================================================
    #  运行
    # ============================================================
    def _stop_engine(self):
        if hasattr(self, "_engine"):
            self._engine.stop()

    def _run(self, evt=None):
        self._sync_from_ui()
        tmp = os.path.join(self._project_root.get(), "res", "_tmp_workflow.json")
        self._write_json(tmp)
        self._stop_btn.config(state=tk.NORMAL, text="■ 停止运行 (点击停止)")
        def _runner():
            try:
                from openar import ARProject, AdbController, DesktopController, TaskEngine
                project = ARProject.from_json_file(tmp)
                if project.controller_type == 1:
                    region = None
                    if project.desktop_region:
                        parts = [int(x.strip()) for x in project.desktop_region.split(",")]
                        if len(parts) == 4: region = tuple(parts)
                    ctrl = DesktopController(window_title=project.device_path or None,
                                             monitor=project.device_index, region=region)
                else:
                    ctrl = AdbController(adb_path=project.adb_path, adb_port=project.adb_port)
                if not ctrl.connect():
                    self.root.after(0, lambda: messagebox.showerror("连接失败", "无法连接设备/桌面"))
                    return
                self._engine = TaskEngine(project, ctrl)
                self._engine.run()
                ctrl.disconnect()
                self.root.after(0, lambda: messagebox.showinfo("完成", "工作流执行完毕"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("运行失败", str(e)))
            finally:
                self.root.after(0, lambda: self._stop_btn.config(state=tk.DISABLED, text="■ 停止运行"))
                if os.path.exists(tmp): os.remove(tmp)
        threading.Thread(target=_runner, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    WorkflowEditor(root)
    root.mainloop()
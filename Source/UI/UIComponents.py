import tkinter as tk
from tkinter import ttk


class AppUI:
    """UI 组件管理类"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Perforce流一键切换工具")
        self.root.geometry("900x600")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.frame = tk.Frame(root)
        self.frame.grid(row=0, column=0, sticky='nsew')

        for i in range(15):
            self.frame.rowconfigure(i, weight=1)
        self.frame.columnconfigure(1, weight=1)

        # 变量
        self.workspace_tag_var = tk.StringVar()
        self.max_workspace_cnt_var = tk.IntVar(value=5)
        self.available_workspace_var = tk.StringVar(value="0/5")
        self.p4_project_var = tk.StringVar()
        self.p4_stream_var = tk.StringVar()
        self.p4_workspace_var = tk.StringVar()
        self.workspace_preview_var = tk.StringVar()

        self.widgets_default_settings = []
        self._CreateWidgets()

    def _CreateWidgets(self):
        row_idx = 0

        # ========== 通用配置区域 ==========
        general_frame = tk.LabelFrame(self.frame, text="通用配置", padx=10, pady=5)
        general_frame.grid(row=row_idx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        general_frame.columnconfigure(1, weight=1)

        # 工作区标识
        tk.Label(general_frame, text="工作区标识:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.workspace_tag_entry = tk.Entry(general_frame, textvariable=self.workspace_tag_var)
        self.workspace_tag_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.workspace_tag_entry, 'normal', self.workspace_tag_entry.cget('fg')])

        # 最大工作区
        tk.Label(general_frame, text="最大工作区:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.max_workspace_spinbox = tk.Spinbox(general_frame, from_=1, to=99, textvariable=self.max_workspace_cnt_var, width=10)
        self.max_workspace_spinbox.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.widgets_default_settings.append([self.max_workspace_spinbox, 'normal', ''])

        row_idx += 1

        # ========== 工作区配置区域 ==========
        workspace_frame = tk.LabelFrame(self.frame, text="工作区配置", padx=10, pady=5)
        workspace_frame.grid(row=row_idx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        workspace_frame.columnconfigure(1, weight=1)

        # 选择流项目
        tk.Label(workspace_frame, text="选择流项目:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.project_combo = ttk.Combobox(workspace_frame, textvariable=self.p4_project_var, state='readonly')
        self.project_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.project_combo, 'readonly', ''])

        # 选择流分支
        tk.Label(workspace_frame, text="选择流分支:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.stream_combo = ttk.Combobox(workspace_frame, textvariable=self.p4_stream_var, state='readonly')
        self.stream_combo.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.stream_combo, 'readonly', ''])

        # 工作区名称
        tk.Label(workspace_frame, text="工作区名称:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.workspace_preview_label = tk.Label(workspace_frame, textvariable=self.workspace_preview_var, fg='gray')
        self.workspace_preview_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        # 工作区目录
        tk.Label(workspace_frame, text="工作区目录:").grid(row=3, column=0, padx=5, pady=5, sticky='e')
        self.workspace_entry = tk.Entry(workspace_frame, textvariable=self.p4_workspace_var, state='readonly', cursor='hand2')
        self.workspace_entry.grid(row=3, column=1, padx=5, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.workspace_entry, 'readonly', self.workspace_entry.cget('fg')])
        self.workspace_default_fg = self.workspace_entry.cget('fg')
        self.workspace_is_default = False

        # 离线目录复选框
        self.offline_var = tk.BooleanVar(value=False)
        self.offline_checkbox = tk.Checkbutton(workspace_frame, text="离线目录（使用 reconcile 保留本地修改）", variable=self.offline_var)
        self.offline_checkbox.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        self.widgets_default_settings.append([self.offline_checkbox, 'normal', ''])

        # 切换并打开按钮
        self.apply_button = tk.Button(workspace_frame, text="切换并打开 P4V")
        self.apply_button.grid(row=5, column=0, columnspan=2, pady=10)
        self.widgets_default_settings.append([self.apply_button, 'normal', self.apply_button.cget('fg')])

        row_idx += 1

        # ========== 进度条 ==========
        self.progress_bar = ttk.Progressbar(self.frame, mode='determinate')
        self.progress_label_frame = tk.Frame(self.frame)
        self.progress_label_frame.grid_columnconfigure(0, weight=1)
        self.progress_label_frame.grid_columnconfigure(1, weight=1)

        self.operation_label = tk.Label(self.progress_label_frame, text="")
        self.operation_label.grid(row=0, column=0, sticky='w')

        self.progress_percentage_label = tk.Label(self.progress_label_frame, text="0%")
        self.progress_percentage_label.grid(row=0, column=1, sticky='e')

        self.progress_bar.grid(row=row_idx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        self.progress_label_frame.grid(row=row_idx+1, column=0, columnspan=3, sticky='ew')
        self.progress_bar.grid_remove()
        self.progress_label_frame.grid_remove()

        row_idx += 2

        # ========== 日志输出区 ==========
        log_frame = tk.LabelFrame(self.frame, text="日志输出", padx=10, pady=5)
        log_frame.grid(row=row_idx, column=0, columnspan=3, padx=10, pady=5, sticky='nsew')
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=10, state='disabled')
        self.log_text.grid(row=0, column=0, sticky='nsew')

        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.frame.rowconfigure(row_idx, weight=3)

        row_idx += 1

        # ========== 状态栏 ==========
        self.cur_client_var = tk.StringVar()
        status_frame = tk.Frame(self.frame)
        status_frame.grid(row=row_idx, column=0, columnspan=3, padx=10, pady=2, sticky='ew')
        status_frame.columnconfigure(0, weight=1)

        self.cur_client_label = tk.Label(status_frame, textvariable=self.cur_client_var, anchor='w')
        self.cur_client_label.grid(row=0, column=0, sticky='w')

        self.available_workspace_label = tk.Label(status_frame, textvariable=self.available_workspace_var, anchor='e')
        self.available_workspace_label.grid(row=0, column=1, sticky='e')

    def LogMessage(self, message: str):
        """在日志区添加消息"""
        def append():
            self.log_text.configure(state='normal')
            self.log_text.insert('end', message + '\n')
            self.log_text.configure(state='disabled')
            self.log_text.see('end')
        self.root.after(0, append)

    def ClearLog(self):
        """清空日志"""
        def clear():
            self.log_text.configure(state='normal')
            self.log_text.delete('1.0', tk.END)
            self.log_text.configure(state='disabled')
        self.root.after(0, clear)

    def UpdateProgress(self, current: int, total: int):
        """更新进度条"""
        percentage = int((current / total) * 100)
        def update():
            self.progress_bar['value'] = percentage
            self.progress_percentage_label.configure(text=f"{percentage}%")
        self.root.after(0, update)

    def UpdateOperationLabel(self, text: str):
        """更新当前操作标签"""
        def update():
            self.operation_label.configure(text=text)
        self.root.after(0, update)

    def ShowProgressBar(self):
        """显示进度条"""
        def show():
            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = 100
            self.progress_bar.grid()
            self.progress_label_frame.grid()
            self.progress_percentage_label.configure(text="0%")
        self.root.after(0, show)

    def HideProgressBar(self):
        """隐藏进度条"""
        def hide():
            self.progress_bar.grid_remove()
            self.progress_label_frame.grid_remove()
        self.root.after(0, hide)

    def DisableUI(self):
        """禁用所有输入控件"""
        for widget, default_state, default_fg in self.widgets_default_settings:
            widget.configure(state='disabled')
            if default_fg:
                widget.configure(fg='grey')

    def EnableUI(self):
        """启用所有输入控件"""
        for widget, default_state, default_fg in self.widgets_default_settings:
            widget.configure(state=default_state)
            if default_fg:
                widget.configure(fg=default_fg)

    def SetWorkspaceSource(self, is_cached: bool):
        """设置工作区路径来源颜色（缓存=正常，默认=灰色）"""
        self.workspace_is_default = not is_cached
        if is_cached:
            self.workspace_entry.configure(fg=self.workspace_default_fg)
        else:
            self.workspace_entry.configure(fg='grey')

    def SetWorkspaceSourceManual(self):
        """设置工作区路径来源为手动选择（正常颜色）"""
        self.workspace_is_default = False
        self.workspace_entry.configure(fg=self.workspace_default_fg)

    def UpdateWorkspacePreview(self, name: str, exists: bool):
        """更新工作区名称预览"""
        self.workspace_preview_var.set(name)
        self.workspace_preview_label.configure(fg='black' if exists else 'gray')

    def UpdateAvailableWorkspace(self, available: int, max_cnt: int):
        """更新可用工作区显示"""
        self.available_workspace_var.set(f"可用工作区: {available}/{max_cnt}")

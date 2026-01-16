import tkinter as tk
from tkinter import ttk


class AppUI:
    """UI 组件管理类"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Perforce流一键切换工具")
        self.root.geometry("700x500")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.frame = tk.Frame(root)
        self.frame.grid(row=0, column=0, sticky='nsew')
        self.frame.columnconfigure(0, weight=1)

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
        RowIdx = 0

        # ========== 通用配置区域 ==========
        GeneralFrame = tk.LabelFrame(self.frame, text="通用配置", padx=10, pady=5)
        GeneralFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        GeneralFrame.columnconfigure(1, weight=1)

        # 工作区标识
        tk.Label(GeneralFrame, text="工作区标识:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        TagFrame = tk.Frame(GeneralFrame)
        TagFrame.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        TagFrame.columnconfigure(0, weight=1)

        self.workspace_tag_entry = tk.Entry(TagFrame, textvariable=self.workspace_tag_var)
        self.workspace_tag_entry.grid(row=0, column=0, sticky='ew')
        self.widgets_default_settings.append([self.workspace_tag_entry, 'normal', self.workspace_tag_entry.cget('fg')])

        self.tag_status_label = tk.Label(TagFrame, text="", width=2)
        self.tag_status_label.grid(row=0, column=1, padx=2)

        self.tag_save_button = tk.Button(TagFrame, text="保存", state='disabled')
        self.tag_save_button.grid(row=0, column=2, padx=2)
        self.widgets_default_settings.append([self.tag_save_button, 'disabled', ''])

        # 最大工作区 + 创建 P4CONFIG + 自动删除空文件夹（并排）
        OptionsFrame = tk.Frame(GeneralFrame)
        OptionsFrame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        tk.Label(OptionsFrame, text="最大工作区:").grid(row=0, column=0, padx=(0, 5))
        self.max_workspace_spinbox = tk.Spinbox(OptionsFrame, from_=1, to=99, textvariable=self.max_workspace_cnt_var, width=5)
        self.max_workspace_spinbox.grid(row=0, column=1, padx=(0, 20))
        self.widgets_default_settings.append([self.max_workspace_spinbox, 'normal', ''])

        self.create_p4config_var = tk.BooleanVar(value=True)
        self.create_p4config_checkbox = tk.Checkbutton(OptionsFrame, text="创建 P4CONFIG", variable=self.create_p4config_var)
        self.create_p4config_checkbox.grid(row=0, column=2, padx=(0, 20))
        self.widgets_default_settings.append([self.create_p4config_checkbox, 'normal', ''])

        self.auto_rmdir_var = tk.BooleanVar(value=True)
        self.auto_rmdir_checkbox = tk.Checkbutton(OptionsFrame, text="自动删除空文件夹", variable=self.auto_rmdir_var)
        self.auto_rmdir_checkbox.grid(row=0, column=3)
        self.widgets_default_settings.append([self.auto_rmdir_checkbox, 'normal', ''])

        RowIdx += 1

        # ========== 工作区配置区域 ==========
        WorkspaceFrame = tk.LabelFrame(self.frame, text="工作区配置", padx=10, pady=5)
        WorkspaceFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        WorkspaceFrame.columnconfigure(1, weight=1)
        WorkspaceFrame.columnconfigure(3, weight=1)

        # 第一行：项目 + 分支
        tk.Label(WorkspaceFrame, text="项目:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.project_combo = ttk.Combobox(WorkspaceFrame, textvariable=self.p4_project_var, state='readonly')
        self.project_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.project_combo, 'readonly', ''])

        tk.Label(WorkspaceFrame, text="分支:").grid(row=0, column=2, padx=5, pady=5, sticky='e')
        self.stream_combo = ttk.Combobox(WorkspaceFrame, textvariable=self.p4_stream_var, state='readonly')
        self.stream_combo.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.stream_combo, 'readonly', ''])

        # 第二行：名称 + 目录
        tk.Label(WorkspaceFrame, text="名称:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.workspace_preview_label = tk.Label(WorkspaceFrame, textvariable=self.workspace_preview_var, fg='gray')
        self.workspace_preview_label.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        tk.Label(WorkspaceFrame, text="目录:").grid(row=1, column=2, padx=5, pady=5, sticky='e')
        self.workspace_entry = tk.Entry(WorkspaceFrame, textvariable=self.p4_workspace_var, state='readonly', cursor='hand2')
        self.workspace_entry.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.workspace_entry, 'readonly', self.workspace_entry.cget('fg')])
        self.workspace_default_fg = self.workspace_entry.cget('fg')
        self.workspace_is_default = False

        # 第三行：离线目录复选框（居中）
        self.offline_var = tk.BooleanVar(value=False)
        self.offline_checkbox = tk.Checkbutton(WorkspaceFrame, text="离线目录（创建时以本地文件为准）", variable=self.offline_var)
        self.offline_checkbox.grid(row=2, column=0, columnspan=4, pady=5)
        self.widgets_default_settings.append([self.offline_checkbox, 'normal', ''])

        # 第四行：切换按钮
        self.apply_button = tk.Button(WorkspaceFrame, text="切换并打开 P4V")
        self.apply_button.grid(row=3, column=0, columnspan=4, pady=10)
        self.widgets_default_settings.append([self.apply_button, 'normal', self.apply_button.cget('fg')])

        RowIdx += 1

        # ========== 进度条 ==========
        self.progress_bar = ttk.Progressbar(self.frame, mode='determinate')
        self.progress_label_frame = tk.Frame(self.frame)
        self.progress_label_frame.grid_columnconfigure(0, weight=1)
        self.progress_label_frame.grid_columnconfigure(1, weight=1)

        self.operation_label = tk.Label(self.progress_label_frame, text="")
        self.operation_label.grid(row=0, column=0, sticky='w')

        self.progress_percentage_label = tk.Label(self.progress_label_frame, text="0%")
        self.progress_percentage_label.grid(row=0, column=1, sticky='e')

        self.progress_bar.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        self.progress_label_frame.grid(row=RowIdx+1, column=0, columnspan=3, sticky='ew')
        self.progress_bar.grid_remove()
        self.progress_label_frame.grid_remove()

        RowIdx += 2

        # ========== 日志输出区 ==========
        LogFrame = tk.LabelFrame(self.frame, text="日志输出", padx=10, pady=5)
        LogFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='nsew')
        LogFrame.rowconfigure(0, weight=1)
        LogFrame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(LogFrame, height=10, state='disabled')
        self.log_text.grid(row=0, column=0, sticky='nsew')

        Scrollbar = tk.Scrollbar(LogFrame, command=self.log_text.yview)
        Scrollbar.grid(row=0, column=1, sticky='ns')
        self.log_text.configure(yscrollcommand=Scrollbar.set)

        self.frame.rowconfigure(RowIdx, weight=1)

        RowIdx += 1

        # ========== 状态栏 ==========
        self.server_user_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        self._blink_state = False
        self._blink_job = None
        StatusFrame = tk.Frame(self.frame)
        StatusFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=(0, 5), sticky='sew')
        StatusFrame.columnconfigure(2, weight=1)

        # 状态指示点
        self.status_dot = tk.Label(StatusFrame, text="●", fg='green', font=('Arial', 10))
        self.status_dot.grid(row=0, column=0, padx=(0, 3))

        self.status_label = tk.Label(StatusFrame, textvariable=self.status_var, anchor='w')
        self.status_label.grid(row=0, column=1, sticky='w')

        self.server_user_label = tk.Label(StatusFrame, textvariable=self.server_user_var, anchor='center')
        self.server_user_label.grid(row=0, column=2)

        self.used_workspace_label = tk.Label(StatusFrame, textvariable=self.available_workspace_var, anchor='e')
        self.used_workspace_label.grid(row=0, column=3, sticky='e')

    def LogMessage(self, Msg: str):
        """在日志区添加消息"""
        def Append():
            self.log_text.configure(state='normal')
            self.log_text.insert('end', Msg + '\n')
            self.log_text.configure(state='disabled')
            self.log_text.see('end')
        self.root.after(0, Append)

    def ClearLog(self):
        """清空日志"""
        def Clear():
            self.log_text.configure(state='normal')
            self.log_text.delete('1.0', tk.END)
            self.log_text.configure(state='disabled')
        self.root.after(0, Clear)

    def UpdateProgress(self, Cur: int, Total: int):
        """更新进度条"""
        Pct = int((Cur / Total) * 100)
        def DoUpdate():
            self.progress_bar['value'] = Pct
            self.progress_percentage_label.configure(text=f"{Pct}%")
        self.root.after(0, DoUpdate)

    def UpdateOperationLabel(self, Text: str):
        """更新当前操作标签"""
        def DoUpdate():
            self.operation_label.configure(text=Text)
        self.root.after(0, DoUpdate)

    def ShowProgressBar(self):
        """显示进度条"""
        def Show():
            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = 100
            self.progress_bar.grid()
            self.progress_label_frame.grid()
            self.progress_percentage_label.configure(text="0%")
        self.root.after(0, Show)

    def HideProgressBar(self):
        """隐藏进度条"""
        def Hide():
            self.progress_bar.grid_remove()
            self.progress_label_frame.grid_remove()
        self.root.after(0, Hide)

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

    def UpdateUsedWorkspace(self, used: int, max_cnt: int):
        """更新使用工作区显示"""
        self.available_workspace_var.set(f"使用工作区: {used}/{max_cnt}")

    def SetTagStatus(self, Valid: bool, Empty: bool = False):
        """设置标识验证状态"""
        if Empty:
            self.tag_status_label.configure(text="", fg='black')
            self.tag_save_button.configure(state='disabled')
        elif Valid:
            self.tag_status_label.configure(text="O", fg='green')
        else:
            self.tag_status_label.configure(text="X", fg='red')
            self.tag_save_button.configure(state='disabled')

    def EnableTagSave(self, Enable: bool):
        """启用或禁用标识保存按钮"""
        self.tag_save_button.configure(state='normal' if Enable else 'disabled')

    def UpdateStatus(self, Text: str, Color: str = None, Blink: bool = False):
        """更新状态栏状态文本和指示点颜色"""
        def Update():
            self.status_var.set(Text)
            if Color:
                self._SetDotColor(Color, Blink)
        self.root.after(0, Update)

    def _SetDotColor(self, Color: str, Blink: bool = False):
        """设置状态点颜色和闪烁"""
        # 停止之前的闪烁
        if self._blink_job:
            self.root.after_cancel(self._blink_job)
            self._blink_job = None

        self.status_dot.configure(fg=Color)
        self._blink_state = True

        if Blink:
            self._StartBlink(Color)

    def _StartBlink(self, Color: str):
        """开始闪烁"""
        def DoBlink():
            self._blink_state = not self._blink_state
            self.status_dot.configure(fg=Color if self._blink_state else 'gray')
            self._blink_job = self.root.after(500, DoBlink)
        DoBlink()

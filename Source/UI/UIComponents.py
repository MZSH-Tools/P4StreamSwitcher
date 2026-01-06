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
        self.p4_server_var = tk.StringVar()
        self.p4_user_var = tk.StringVar()
        self.p4_client_var = tk.StringVar()
        self.p4_project_var = tk.StringVar()
        self.p4_stream_var = tk.StringVar()
        self.p4_workspace_var = tk.StringVar()
        self.auto_sync_var = tk.BooleanVar(value=True)
        self.auto_clean_var = tk.BooleanVar(value=True)

        self.widgets_default_settings = []
        self._CreateWidgets()

    def _CreateWidgets(self):
        row_index = 0

        # 服务器
        tk.Label(self.frame, text="服务器:").grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
        self.server_entry = tk.Entry(self.frame, textvariable=self.p4_server_var, state='readonly')
        self.server_entry.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.server_entry, 'readonly', self.server_entry.cget('fg')])

        row_index += 1
        # 用户
        tk.Label(self.frame, text="用户:").grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
        self.user_entry = tk.Entry(self.frame, textvariable=self.p4_user_var, state='readonly')
        self.user_entry.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.user_entry, 'readonly', self.user_entry.cget('fg')])

        row_index += 1
        # 流客户端
        tk.Label(self.frame, text="流客户端:").grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
        self.client_combo = ttk.Combobox(self.frame, textvariable=self.p4_client_var, state='readonly')
        self.client_combo.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.client_combo, 'readonly', ''])

        row_index += 1
        # 流项目
        tk.Label(self.frame, text="选择流项目:").grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
        self.project_combo = ttk.Combobox(self.frame, textvariable=self.p4_project_var, state='readonly')
        self.project_combo.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.project_combo, 'readonly', ''])

        row_index += 1
        # 流分支
        tk.Label(self.frame, text="选择流分支:").grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
        self.stream_combo = ttk.Combobox(self.frame, textvariable=self.p4_stream_var, state='readonly')
        self.stream_combo.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.stream_combo, 'readonly', ''])

        row_index += 1
        # 工作区目录
        tk.Label(self.frame, text="工作区目录:").grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
        self.workspace_entry = tk.Entry(self.frame, textvariable=self.p4_workspace_var)
        self.workspace_entry.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
        self.widgets_default_settings.append([self.workspace_entry, 'normal', self.workspace_entry.cget('fg')])

        row_index += 1
        # 自动链接复选框
        self.auto_sync_check = tk.Checkbutton(self.frame, text="自动链接服务器文件", variable=self.auto_sync_var)
        self.auto_sync_check.grid(row=row_index, column=1, sticky='w')
        self.widgets_default_settings.append([self.auto_sync_check, 'normal', self.auto_sync_check.cget('fg')])

        row_index += 1
        # 自动清理复选框
        self.auto_clean_check = tk.Checkbutton(self.frame, text="自动清理多余文件（根据 .p4ignore 保留缓存）", variable=self.auto_clean_var)
        self.auto_clean_check.grid(row=row_index, column=1, sticky='w')
        self.widgets_default_settings.append([self.auto_clean_check, 'normal', self.auto_clean_check.cget('fg')])

        row_index += 1
        # 一键应用按钮
        self.apply_button = tk.Button(self.frame, text="一键应用")
        self.apply_button.grid(row=row_index, column=0, columnspan=2, pady=10)
        self.widgets_default_settings.append([self.apply_button, 'normal', self.apply_button.cget('fg')])

        row_index += 1
        # 进度条
        self.progress_bar = ttk.Progressbar(self.frame, mode='determinate')
        self.progress_label_frame = tk.Frame(self.frame)
        self.progress_label_frame.grid_columnconfigure(0, weight=1)
        self.progress_label_frame.grid_columnconfigure(1, weight=1)

        self.operation_label = tk.Label(self.progress_label_frame, text="")
        self.operation_label.grid(row=0, column=0, sticky='w')

        self.progress_percentage_label = tk.Label(self.progress_label_frame, text="0%")
        self.progress_percentage_label.grid(row=0, column=1, sticky='e')

        self.progress_bar.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
        self.progress_label_frame.grid(row=row_index+1, column=0, columnspan=2, sticky='ew')
        self.progress_bar.grid_remove()
        self.progress_label_frame.grid_remove()

        row_index += 2
        # 日志输出区
        tk.Label(self.frame, text="日志输出：").grid(row=row_index, column=0, padx=10, pady=5, sticky='nw')

        self.log_text = tk.Text(self.frame, height=10, state='disabled')
        self.log_text.grid(row=row_index, column=1, padx=10, pady=5, sticky='nsew')

        scrollbar = tk.Scrollbar(self.frame, command=self.log_text.yview)
        scrollbar.grid(row=row_index, column=2, sticky='ns')
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.frame.rowconfigure(row_index, weight=3)

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

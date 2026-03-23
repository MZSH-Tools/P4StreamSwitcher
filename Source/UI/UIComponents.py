import tkinter as tk
from tkinter import ttk
from datetime import datetime


class LogLevel:
    """日志级别常量"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AppUI:
    """UI 组件管理类"""

    def __init__(self, root: tk.Tk):
        self.Root = root
        self.Root.title("Perforce流一键切换工具")
        # 窗口居中
        Width, Height = 700, 500
        ScreenWidth = self.Root.winfo_screenwidth()
        ScreenHeight = self.Root.winfo_screenheight()
        X = (ScreenWidth - Width) // 2
        Y = (ScreenHeight - Height) // 2
        self.Root.geometry(f"{Width}x{Height}+{X}+{Y}")

        self.Root.rowconfigure(0, weight=1)
        self.Root.columnconfigure(0, weight=1)

        self.Frame = tk.Frame(root)
        self.Frame.grid(row=0, column=0, sticky='nsew')
        self.Frame.columnconfigure(0, weight=1)

        # 变量
        self.WorkspaceTagVar = tk.StringVar()
        self.MaxWorkspaceCntVar = tk.IntVar(value=5)
        self.AvailableWorkspaceVar = tk.StringVar(value="0/5")
        self.P4ProjectVar = tk.StringVar()
        self.P4StreamVar = tk.StringVar()
        self.P4WorkspaceVar = tk.StringVar()
        self.WorkspacePreviewVar = tk.StringVar()

        self.WidgetsDefaultSettings = []
        self.CreateWidgets()

    def CreateWidgets(self):
        RowIdx = 0

        # ========== 通用配置区域 ==========
        GeneralFrame = tk.LabelFrame(self.Frame, text="通用配置", padx=10, pady=5)
        GeneralFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        GeneralFrame.columnconfigure(1, weight=1)

        # 工作区标识
        tk.Label(GeneralFrame, text="工作区标识:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        TagFrame = tk.Frame(GeneralFrame)
        TagFrame.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        TagFrame.columnconfigure(0, weight=1)

        self.WorkspaceTagEntry = tk.Entry(TagFrame, textvariable=self.WorkspaceTagVar)
        self.WorkspaceTagEntry.grid(row=0, column=0, sticky='ew')
        self.WidgetsDefaultSettings.append([self.WorkspaceTagEntry, 'normal', self.WorkspaceTagEntry.cget('fg')])

        self.TagStatusLabel = tk.Label(TagFrame, text="", width=2)
        self.TagStatusLabel.grid(row=0, column=1, padx=2)

        self.TagSaveButton = tk.Button(TagFrame, text="保存", state='disabled')
        self.TagSaveButton.grid(row=0, column=2, padx=2)
        self.WidgetsDefaultSettings.append([self.TagSaveButton, 'disabled', ''])

        # 最大工作区 + 创建 P4CONFIG + 自动删除空文件夹（并排）
        OptionsFrame = tk.Frame(GeneralFrame)
        OptionsFrame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        tk.Label(OptionsFrame, text="最大工作区:").grid(row=0, column=0, padx=(0, 5))
        self.MaxWorkspaceSpinbox = tk.Spinbox(OptionsFrame, from_=1, to=99, textvariable=self.MaxWorkspaceCntVar, width=5)
        self.MaxWorkspaceSpinbox.grid(row=0, column=1, padx=(0, 20))
        self.WidgetsDefaultSettings.append([self.MaxWorkspaceSpinbox, 'normal', ''])

        self.CreateP4ConfigVar = tk.BooleanVar(value=True)
        self.CreateP4ConfigCheckbox = tk.Checkbutton(OptionsFrame, text="创建 P4CONFIG", variable=self.CreateP4ConfigVar)
        self.CreateP4ConfigCheckbox.grid(row=0, column=2, padx=(0, 20))
        self.WidgetsDefaultSettings.append([self.CreateP4ConfigCheckbox, 'normal', ''])

        self.AutoRmdirVar = tk.BooleanVar(value=True)
        self.AutoRmdirCheckbox = tk.Checkbutton(OptionsFrame, text="自动删除空文件夹", variable=self.AutoRmdirVar)
        self.AutoRmdirCheckbox.grid(row=0, column=3)
        self.WidgetsDefaultSettings.append([self.AutoRmdirCheckbox, 'normal', ''])

        RowIdx += 1

        # ========== 工作区配置区域 ==========
        WorkspaceFrame = tk.LabelFrame(self.Frame, text="工作区配置", padx=10, pady=5)
        WorkspaceFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        WorkspaceFrame.columnconfigure(1, weight=1)
        WorkspaceFrame.columnconfigure(3, weight=1)

        # 第一行：项目 + 分支
        tk.Label(WorkspaceFrame, text="项目:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.ProjectCombo = ttk.Combobox(WorkspaceFrame, textvariable=self.P4ProjectVar, state='readonly')
        self.ProjectCombo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.WidgetsDefaultSettings.append([self.ProjectCombo, 'readonly', ''])

        tk.Label(WorkspaceFrame, text="分支:").grid(row=0, column=2, padx=5, pady=5, sticky='e')
        self.StreamCombo = ttk.Combobox(WorkspaceFrame, textvariable=self.P4StreamVar, state='readonly')
        self.StreamCombo.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        self.WidgetsDefaultSettings.append([self.StreamCombo, 'readonly', ''])

        # 第二行：名称 + 目录
        tk.Label(WorkspaceFrame, text="名称:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.WorkspacePreviewLabel = tk.Label(WorkspaceFrame, textvariable=self.WorkspacePreviewVar, fg='gray')
        self.WorkspacePreviewLabel.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        tk.Label(WorkspaceFrame, text="目录:").grid(row=1, column=2, padx=5, pady=5, sticky='e')
        self.WorkspaceEntry = tk.Entry(WorkspaceFrame, textvariable=self.P4WorkspaceVar, state='readonly', cursor='hand2')
        self.WorkspaceEntry.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
        self.WidgetsDefaultSettings.append([self.WorkspaceEntry, 'readonly', self.WorkspaceEntry.cget('fg')])
        self.WorkspaceDefaultFg = self.WorkspaceEntry.cget('fg')
        self.WorkspaceIsDefault = False
        self.WorkspaceIsManual = False

        # 第三行：离线目录复选框（居中）
        self.OfflineVar = tk.BooleanVar(value=False)
        self.OfflineCheckbox = tk.Checkbutton(WorkspaceFrame, text="离线目录（创建时以本地文件为准）", variable=self.OfflineVar)
        self.OfflineCheckbox.grid(row=2, column=0, columnspan=4, pady=5)
        self.WidgetsDefaultSettings.append([self.OfflineCheckbox, 'normal', ''])

        # 第四行：切换按钮 + 删除按钮
        ButtonFrame = tk.Frame(WorkspaceFrame)
        ButtonFrame.grid(row=3, column=0, columnspan=4, pady=10)

        self.ApplyButton = tk.Button(ButtonFrame, text="切换并打开 P4V")
        self.ApplyButton.grid(row=0, column=0, padx=(0, 10))
        self.WidgetsDefaultSettings.append([self.ApplyButton, 'normal', self.ApplyButton.cget('fg')])

        self.DeleteButton = tk.Button(ButtonFrame, text="删除工作区", fg='red')
        self.DeleteButton.grid(row=0, column=1)
        self.WidgetsDefaultSettings.append([self.DeleteButton, 'normal', 'red'])

        RowIdx += 1

        # ========== 进度条 ==========
        self.ProgressBar = ttk.Progressbar(self.Frame, mode='determinate')
        self.ProgressLabelFrame = tk.Frame(self.Frame)
        self.ProgressLabelFrame.grid_columnconfigure(0, weight=1)
        self.ProgressLabelFrame.grid_columnconfigure(1, weight=1)

        self.OperationLabel = tk.Label(self.ProgressLabelFrame, text="")
        self.OperationLabel.grid(row=0, column=0, sticky='w')

        self.ProgressPctLabel = tk.Label(self.ProgressLabelFrame, text="0%")
        self.ProgressPctLabel.grid(row=0, column=1, sticky='e')

        self.ProgressBar.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        self.ProgressLabelFrame.grid(row=RowIdx+1, column=0, columnspan=3, sticky='ew')
        self.ProgressBar.grid_remove()
        self.ProgressLabelFrame.grid_remove()

        RowIdx += 2

        # ========== 日志输出区 ==========
        LogFrame = tk.LabelFrame(self.Frame, text="日志输出", padx=10, pady=5)
        LogFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=5, sticky='nsew')
        LogFrame.rowconfigure(0, weight=1)
        LogFrame.columnconfigure(0, weight=1)

        self.LogText = tk.Text(LogFrame, height=10, state='disabled')
        self.LogText.grid(row=0, column=0, sticky='nsew')

        # 配置日志级别颜色标签
        self.LogText.tag_configure(LogLevel.INFO, foreground='black')
        self.LogText.tag_configure(LogLevel.WARNING, foreground='orange')
        self.LogText.tag_configure(LogLevel.ERROR, foreground='red')

        Scrollbar = tk.Scrollbar(LogFrame, command=self.LogText.yview)
        Scrollbar.grid(row=0, column=1, sticky='ns')
        self.LogText.configure(yscrollcommand=Scrollbar.set)

        self.Frame.rowconfigure(RowIdx, weight=1)

        RowIdx += 1

        # ========== 状态栏 ==========
        self.ServerUserVar = tk.StringVar()
        self.StatusVar = tk.StringVar(value="就绪")
        self.BlinkState = False
        self.BlinkJob = None
        StatusFrame = tk.Frame(self.Frame)
        StatusFrame.grid(row=RowIdx, column=0, columnspan=3, padx=10, pady=(0, 5), sticky='sew')
        StatusFrame.columnconfigure(2, weight=1)

        # 状态指示点
        self.StatusDot = tk.Label(StatusFrame, text="●", fg='green', font=('Arial', 10))
        self.StatusDot.grid(row=0, column=0, padx=(0, 3))

        self.StatusLabel = tk.Label(StatusFrame, textvariable=self.StatusVar, anchor='w')
        self.StatusLabel.grid(row=0, column=1, sticky='w')

        self.ServerUserLabel = tk.Label(StatusFrame, textvariable=self.ServerUserVar, anchor='center')
        self.ServerUserLabel.grid(row=0, column=2)

        self.UsedWorkspaceLabel = tk.Label(StatusFrame, textvariable=self.AvailableWorkspaceVar, anchor='e')
        self.UsedWorkspaceLabel.grid(row=0, column=3, sticky='e')

    def LogMessage(self, Msg: str, Level: str = LogLevel.INFO, ShowTime: bool = True):
        """在日志区添加消息"""
        def Append():
            self.LogText.configure(state='normal')
            if ShowTime:
                TimeStr = datetime.now().strftime("[%H:%M:%S] ")
                self.LogText.insert('end', TimeStr)
            self.LogText.insert('end', Msg + '\n', Level)
            self.LogText.configure(state='disabled')
            self.LogText.see('end')
        self.Root.after(0, Append)

    def LogInfo(self, Msg: str):
        """记录信息级别日志"""
        self.LogMessage(Msg, LogLevel.INFO)

    def LogWarning(self, Msg: str):
        """记录警告级别日志"""
        self.LogMessage(Msg, LogLevel.WARNING)

    def LogError(self, Msg: str):
        """记录错误级别日志"""
        self.LogMessage(Msg, LogLevel.ERROR)

    def ClearLog(self):
        """清空日志"""
        def Clear():
            self.LogText.configure(state='normal')
            self.LogText.delete('1.0', tk.END)
            self.LogText.configure(state='disabled')
        self.Root.after(0, Clear)

    def UpdateProgress(self, Cur: int, Total: int):
        """更新进度条"""
        Pct = int((Cur / Total) * 100)
        def DoUpdate():
            self.ProgressBar['value'] = Pct
            self.ProgressPctLabel.configure(text=f"{Pct}%")
        self.Root.after(0, DoUpdate)

    def UpdateOperationLabel(self, Text: str):
        """更新当前操作标签"""
        def DoUpdate():
            self.OperationLabel.configure(text=Text)
        self.Root.after(0, DoUpdate)

    def ShowProgressBar(self):
        """显示进度条"""
        def Show():
            self.ProgressBar['value'] = 0
            self.ProgressBar['maximum'] = 100
            self.ProgressBar.grid()
            self.ProgressLabelFrame.grid()
            self.ProgressPctLabel.configure(text="0%")
        self.Root.after(0, Show)

    def HideProgressBar(self):
        """隐藏进度条"""
        def Hide():
            self.ProgressBar.grid_remove()
            self.ProgressLabelFrame.grid_remove()
        self.Root.after(0, Hide)

    def DisableUI(self):
        """禁用所有输入控件"""
        for Widget, DefaultState, DefaultFg in self.WidgetsDefaultSettings:
            Widget.configure(state='disabled')
            if DefaultFg:
                Widget.configure(fg='grey')

    def EnableUI(self):
        """启用所有输入控件"""
        for Widget, DefaultState, DefaultFg in self.WidgetsDefaultSettings:
            Widget.configure(state=DefaultState)
            if DefaultFg:
                Widget.configure(fg=DefaultFg)

    def SetWorkspaceSource(self, IsCached: bool):
        """设置工作区路径来源颜色（缓存=正常，默认=灰色）"""
        self.WorkspaceIsDefault = not IsCached
        self.WorkspaceIsManual = False
        if IsCached:
            self.WorkspaceEntry.configure(fg=self.WorkspaceDefaultFg)
        else:
            self.WorkspaceEntry.configure(fg='grey')

    def SetWorkspaceSourceManual(self):
        """设置工作区路径来源为手动选择（正常颜色）"""
        self.WorkspaceIsDefault = False
        self.WorkspaceIsManual = True
        self.WorkspaceEntry.configure(fg=self.WorkspaceDefaultFg)

    def UpdateWorkspacePreview(self, Name: str, Exists: bool):
        """更新工作区名称预览"""
        self.WorkspacePreviewVar.set(Name)
        self.WorkspacePreviewLabel.configure(fg='black' if Exists else 'gray')

    def UpdateUsedWorkspace(self, Used: int, MaxCnt: int):
        """更新使用工作区显示"""
        self.AvailableWorkspaceVar.set(f"使用工作区: {Used}/{MaxCnt}")

    def SetTagStatus(self, Valid: bool, Empty: bool = False):
        """设置标识验证状态"""
        if Empty:
            self.TagStatusLabel.configure(text="", fg='black')
            self.TagSaveButton.configure(state='disabled')
        elif Valid:
            self.TagStatusLabel.configure(text="O", fg='green')
        else:
            self.TagStatusLabel.configure(text="X", fg='red')
            self.TagSaveButton.configure(state='disabled')

    def EnableTagSave(self, Enable: bool):
        """启用或禁用标识保存按钮"""
        self.TagSaveButton.configure(state='normal' if Enable else 'disabled')

    def UpdateStatus(self, Text: str, Color: str = None, Blink: bool = False):
        """更新状态栏状态文本和指示点颜色"""
        def Update():
            self.StatusVar.set(Text)
            if Color:
                self.SetDotColor(Color, Blink)
        self.Root.after(0, Update)

    def SetDotColor(self, Color: str, Blink: bool = False):
        """设置状态点颜色和闪烁"""
        # 停止之前的闪烁
        if self.BlinkJob:
            self.Root.after_cancel(self.BlinkJob)
            self.BlinkJob = None

        self.StatusDot.configure(fg=Color)
        self.BlinkState = True

        if Blink:
            self.StartBlink(Color)

    def StartBlink(self, Color: str):
        """开始闪烁"""
        def DoBlink():
            self.BlinkState = not self.BlinkState
            self.StatusDot.configure(fg=Color if self.BlinkState else 'gray')
            self.BlinkJob = self.Root.after(500, DoBlink)
        DoBlink()

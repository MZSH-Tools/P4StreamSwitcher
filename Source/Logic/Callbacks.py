import os
import threading
from tkinter import messagebox, filedialog
from P4 import P4, P4Exception

from Source.Data.P4Core import (
    GetClientInfo, GetClientRoot, GetMainlineProjects, GetProjectStreams, ParseStreamPath,
    GetAllStreams, GetOpenedFiles, GetHaveList, GetDifferentFiles, GetMissingFiles,
    SyncFiles, RunSync, P4IgnoreParser, DeleteObsoleteFiles, SyncOutputHandler,
    IsP4GUIRunning, RunReconcile, LaunchP4V, GetAllClients,
    CheckTagConflict, GetLocalClientsWithTag, RenameClient,
    CreateStreamClient, ClientExists, DeleteClient, CreateP4ConfigFile, UpdateClientRmdir
)
from Source.Data.WorkspaceCache import GlobalConfig
from Source.UI.UIComponents import AppUI, LogLevel


class AppCallbacks:
    """应用回调管理类"""

    def __init__(self, P4Conn: P4, UI: AppUI):
        self.P4 = P4Conn
        self.UI = UI

        # 全局配置
        self.GlobalCfg = GlobalConfig()

        # 状态变量
        self.SelectStreamPath = ""
        self.DefaultProject = ""
        self.DefaultStream = ""
        self.DefaultWorkspaceRoot = ""
        self.DefaultStreamPath = ""
        self.CurClient = ""
        self.SavedTag = ""  # 已保存的标识

        self.BindEvents()

    def BindEvents(self):
        """绑定 UI 事件"""
        self.UI.ProjectCombo.bind("<Button-1>", self.OnProjectDropdown)
        self.UI.ProjectCombo.bind("<<ComboboxSelected>>", self.OnProjectSelected)
        self.UI.StreamCombo.bind("<Button-1>", self.OnStreamDropdown)
        self.UI.StreamCombo.bind("<<ComboboxSelected>>", self.OnStreamSelected)
        self.UI.ApplyButton.configure(command=self.OnApply)
        self.UI.WorkspaceEntry.bind("<Button-1>", self.OnWorkspaceClick)
        self.UI.OfflineCheckbox.configure(command=self.OnOfflineChanged)
        # 通用配置事件
        self.UI.WorkspaceTagVar.trace_add("write", self.OnTagVarChanged)
        self.UI.TagSaveButton.configure(command=self.OnTagSave)
        self.UI.MaxWorkspaceSpinbox.bind("<FocusOut>", self.OnMaxWorkspaceCntChanged)
        self.UI.MaxWorkspaceCntVar.trace_add("write", self.OnMaxCntVarChanged)
        self.UI.CreateP4ConfigCheckbox.configure(command=self.OnCreateP4ConfigChanged)
        self.UI.AutoRmdirCheckbox.configure(command=self.OnAutoRmdirChanged)

    def OnTagVarChanged(self, *args):
        """工作区标识变量改变时验证标识并更新状态"""
        Tag = self.UI.WorkspaceTagVar.get().strip()
        self.UpdateWorkspacePreview()
        self.UpdateUsedWorkspace()

        # 空标识
        if not Tag:
            self.UI.SetTagStatus(False, Empty=True)
            return

        # 检查是否与其他主机冲突
        try:
            Conflicts = CheckTagConflict(self.P4, Tag)
            if Conflicts:
                self.UI.SetTagStatus(False)
                return
        except Exception:
            pass

        # 标识有效
        self.UI.SetTagStatus(True)

        # 如果标识与已保存的不同，启用保存按钮
        if Tag != self.SavedTag:
            self.UI.EnableTagSave(True)
        else:
            self.UI.EnableTagSave(False)

    def OnMaxCntVarChanged(self, *args):
        """最大工作区数量变量改变时更新显示"""
        self.UpdateUsedWorkspace()

    def OnTagSave(self):
        """保存标识并重命名本地旧标识工作区"""
        NewTag = self.UI.WorkspaceTagVar.get().strip()
        OldTag = self.SavedTag

        if not NewTag:
            messagebox.showwarning("标识无效", "工作区标识不能为空")
            return

        # 检查冲突
        try:
            Conflicts = CheckTagConflict(self.P4, NewTag)
            if Conflicts:
                messagebox.showwarning("标识冲突", f"该标识已被其他主机使用：\n{', '.join(Conflicts[:5])}")
                return
        except Exception as Err:
            messagebox.showerror("检查失败", f"检查标识时发生错误：{Err}")
            return

        # 重命名旧标识的本地工作区
        if OldTag:
            try:
                OldClients = GetLocalClientsWithTag(self.P4, OldTag)
                if OldClients:
                    Result = messagebox.askyesno("重命名工作区",
                        f"检测到 {len(OldClients)} 个使用旧标识的本地工作区：\n"
                        f"{', '.join(OldClients[:5])}\n\n是否将它们重命名为新标识？")
                    if Result:
                        for OldName in OldClients:
                            # 替换标识前缀
                            Suffix = OldName[len(OldTag):]
                            NewName = f"{NewTag}{Suffix}"
                            try:
                                RenameClient(self.P4, OldName, NewName)
                                # 迁移时间戳
                                self.GlobalCfg.RenameWorkspaceTimestamp(OldName, NewName)
                                self.UI.LogMessage(f"已重命名: {OldName} -> {NewName}")
                            except Exception as Err:
                                self.UI.LogMessage(f"重命名失败 {OldName}: {Err}")
            except Exception as Err:
                self.UI.LogMessage(f"获取旧工作区列表失败: {Err}")

        # 保存配置
        self.GlobalCfg.SetWorkspaceTag(NewTag)
        self.SavedTag = NewTag
        self.UI.EnableTagSave(False)
        self.UI.LogMessage(f"工作区标识已保存: {NewTag}")
        self.UpdateWorkspacePreview()
        self.UpdateUsedWorkspace()

    def OnMaxWorkspaceCntChanged(self, event=None):
        """最大工作区数量改变，保存到缓存"""
        try:
            Cnt = self.UI.MaxWorkspaceCntVar.get()
            if Cnt < 1:
                Cnt = 1
                self.UI.MaxWorkspaceCntVar.set(Cnt)
            self.GlobalCfg.SetMaxWorkspaceCnt(Cnt)
            self.UpdateUsedWorkspace()
        except Exception:
            pass

    def OnCreateP4ConfigChanged(self):
        """创建 P4CONFIG 文件选项改变"""
        self.GlobalCfg.SetCreateP4Config(self.UI.CreateP4ConfigVar.get())

    def OnAutoRmdirChanged(self):
        """自动删除空文件夹选项改变，同步应用到所有本地工作区"""
        AutoRmdir = self.UI.AutoRmdirVar.get()
        self.GlobalCfg.SetAutoRmdir(AutoRmdir)

        # 获取当前标识的所有本地工作区并更新
        Tag = self.UI.WorkspaceTagVar.get().strip()
        if Tag:
            try:
                Clients = GetLocalClientsWithTag(self.P4, Tag)
                for ClientName in Clients:
                    UpdateClientRmdir(self.P4, ClientName, AutoRmdir)
                if Clients:
                    self.UI.LogMessage(f"已更新 {len(Clients)} 个工作区的 rmdir 选项。")
            except Exception as Err:
                self.UI.LogMessage(f"更新工作区选项时出错: {Err}")

    def OnProjectDropdown(self, event=None):
        """项目下拉框点击事件"""
        self.UI.ProjectCombo['values'] = GetMainlineProjects(self.P4)

    def OnProjectSelected(self, event=None):
        """项目选择事件"""
        SelectProject = self.UI.P4ProjectVar.get()
        if SelectProject == self.DefaultProject:
            self.UI.P4StreamVar.set(self.DefaultStream)
            self.SelectStreamPath = self.DefaultStreamPath
        else:
            Streams = GetAllStreams(self.P4)
            for Stream in Streams:
                if Stream.get('Type') == 'mainline':
                    Parsed = ParseStreamPath(Stream.get('Stream', ''))
                    if Parsed[0] == SelectProject:
                        self.UI.P4StreamVar.set(Parsed[1])
                        self.SelectStreamPath = Stream.get('Stream', '')
                        break
        self.UpdateWorkspaceFromCache()
        self.UpdateWorkspacePreview()

    def OnStreamDropdown(self, event=None):
        """分支下拉框点击事件"""
        CurProject = self.UI.P4ProjectVar.get()
        self.UI.StreamCombo['values'] = GetProjectStreams(self.P4, CurProject)

    def OnStreamSelected(self, event=None):
        """分支选择事件"""
        if not self.SelectStreamPath:
            return
        PathArray = self.SelectStreamPath.split('/')[-3:-1]
        if len(PathArray) >= 2:
            self.SelectStreamPath = f"//{PathArray[0]}/{PathArray[1]}/{self.UI.P4StreamVar.get()}"
        self.UpdateWorkspaceFromCache()
        self.UpdateWorkspacePreview()

    def OnApply(self):
        """一键切换按钮点击事件"""
        self.UI.ClearLog()

        # 检查工作区标识
        Tag = self.UI.WorkspaceTagVar.get().strip()
        if not Tag:
            messagebox.showwarning("缺少配置", "请先设置并保存工作区标识")
            return

        # 检查标识是否已保存
        if Tag != self.SavedTag:
            messagebox.showwarning("标识未保存", "请先保存工作区标识")
            return

        TargetWorkspace = self.UI.P4WorkspaceVar.get()
        Project = self.UI.P4ProjectVar.get()
        Stream = self.UI.P4StreamVar.get()
        TargetClientName = f"{Tag}_{Project}_{Stream}"
        MaxCnt = max(1, self.UI.MaxWorkspaceCntVar.get())

        # 获取离线标记
        IsOffline = self.UI.OfflineVar.get()

        # 检查目标工作区是否存在
        TargetExists = ClientExists(self.P4, TargetClientName)

        if TargetExists:
            # 目标工作区已存在
            self.UI.LogMessage(f"目标工作区 {TargetClientName} 已存在。")

            # 更新当前客户端和时间戳
            self.CurClient = TargetClientName
            self.P4.client = TargetClientName
            self.GlobalCfg.UpdateWorkspaceTimestamp(TargetClientName)

            # 保存工作区目录到缓存
            self.GlobalCfg.SetStreamCache(self.SelectStreamPath, TargetWorkspace, IsOffline)

            # 更新或创建 P4CONFIG 文件
            if self.GlobalCfg.GetCreateP4Config():
                CreateP4ConfigFile(TargetWorkspace, TargetClientName, self.P4.port, self.P4.user)
                self.UI.LogMessage(f"已更新 .p4config 文件: {TargetWorkspace}")

            self.ResetDefaultVars()
            self.UpdateUsedWorkspace()

            # 检查是否需要同步
            NeedSync = self.GlobalCfg.GetStreamNeedSync(self.SelectStreamPath)
            if NeedSync:
                self.UI.LogWarning("检测到上次同步未完成，重新执行同步...")
                self.UI.UpdateStatus("正在同步...", "orange", Blink=True)
                self.UI.DisableUI()
                threading.Thread(target=self.RunSyncAndClean, args=(IsOffline,), daemon=True).start()
            else:
                # 直接打开 P4V
                LaunchP4V(self.P4.port, self.P4.user, TargetClientName)
                self.UI.LogMessage("正在启动 P4V...")
                self.UI.UpdateStatus("就绪", "green")
            return

        # === 以下是创建新工作区的逻辑 ===

        # 检查是否使用默认路径，需要用户确认
        if self.UI.WorkspaceIsDefault:
            Result = messagebox.askyesno("确认默认路径",
                f"当前使用自动生成的默认路径：\n\n{TargetWorkspace}\n\n是否使用该路径？")
            if not Result:
                self.UI.LogMessage("用户取消操作。")
                return

        CurrentClients = GetLocalClientsWithTag(self.P4, Tag)
        CurrentCnt = len(CurrentClients)

        if CurrentCnt < MaxCnt:
            # 未达上限，创建新工作区
            self.UI.LogMessage(f"创建新工作区 {TargetClientName}...")
        else:
            # 已达上限，需要删除最旧工作区
            OldestClient = self.GlobalCfg.GetOldestWorkspace(CurrentClients)
            if not OldestClient:
                messagebox.showerror("错误", "无法找到可删除的工作区")
                return

            self.UI.LogMessage(f"已达最大工作区数量 ({CurrentCnt}/{MaxCnt})，需要删除最旧工作区 {OldestClient}...")

            # 检查待删除工作区是否有未提交修改
            OpenedFiles = GetOpenedFiles(self.P4, OldestClient)
            # 检查 P4V 是否正在运行（可能正在使用该工作区）
            P4VRunning = IsP4GUIRunning()

            if OpenedFiles or P4VRunning:
                ErrMsg = f"无法删除工作区 {OldestClient}：\n\n"
                if OpenedFiles:
                    Cnt = len(OpenedFiles)
                    Preview = "\n".join([File.get('depotFile', '') for File in OpenedFiles[:5] if isinstance(File, dict)])
                    ErrMsg += f"• 有 {Cnt} 个未提交文件：\n{Preview}\n\n"
                if P4VRunning:
                    ErrMsg += "• P4V 正在运行中（可能正在使用该工作区）\n\n"
                ErrMsg += "请手动处理后重试。"
                messagebox.showerror("无法删除工作区", ErrMsg)
                self.UI.LogMessage(f"工作区 {OldestClient} 无法删除，操作已取消。")
                return

            # 删除旧工作区
            try:
                DeleteClient(self.P4, OldestClient)
                self.GlobalCfg.RemoveWorkspaceTimestamp(OldestClient)
                self.UI.LogMessage(f"已删除工作区: {OldestClient}")
            except Exception as Err:
                messagebox.showerror("删除失败", f"删除工作区失败：{Err}")
                return

        # 检查目录是否存在
        if not os.path.isdir(TargetWorkspace):
            Result = messagebox.askyesno("目录不存在",
                f"目录 {TargetWorkspace} 不存在。\n\n是否创建该目录并继续切换？")
            if not Result:
                self.UI.LogMessage("用户取消操作。")
                return
            os.makedirs(TargetWorkspace, exist_ok=True)
            self.UI.LogMessage(f"已创建目录: {TargetWorkspace}")

        # 创建新工作区
        self.UI.LogMessage(f"创建工作区: {TargetClientName}")
        self.UI.LogMessage(f"流路径: {self.SelectStreamPath}")
        self.UI.LogMessage(f"工作区目录: {TargetWorkspace}")

        AutoRmdir = self.GlobalCfg.GetAutoRmdir()
        CreateStreamClient(self.P4, TargetClientName, self.SelectStreamPath, TargetWorkspace, AutoRmdir)
        if AutoRmdir:
            self.UI.LogMessage("已启用自动删除空文件夹选项。")

        # 创建 P4CONFIG 文件
        if self.GlobalCfg.GetCreateP4Config():
            CreateP4ConfigFile(TargetWorkspace, TargetClientName, self.P4.port, self.P4.user)
            self.UI.LogMessage(f"已创建 .p4config 文件: {TargetWorkspace}")

        # 更新当前客户端和时间戳
        self.CurClient = TargetClientName
        self.P4.client = TargetClientName
        self.GlobalCfg.UpdateWorkspaceTimestamp(TargetClientName)

        # 保存工作区目录和离线标记到缓存，并设置需要同步标记
        self.GlobalCfg.SetStreamCache(self.SelectStreamPath, TargetWorkspace, IsOffline)
        self.GlobalCfg.SetStreamNeedSync(self.SelectStreamPath, True)

        self.ResetDefaultVars()
        self.UpdateUsedWorkspace()

        # 只有创建新工作区时才执行同步
        self.UI.UpdateStatus("正在同步...", "orange", Blink=True)
        self.UI.DisableUI()
        threading.Thread(target=self.RunSyncAndClean, args=(IsOffline,), daemon=True).start()

    def RunSyncAndClean(self, IsOffline: bool = False):
        """执行同步和清理操作"""
        P4Thread = None
        try:
            self.UI.UpdateOperationLabel("正在连接服务器...")
            CmdTarget = f"//{self.CurClient}/..."
            WorkspaceRoot = self.UI.P4WorkspaceVar.get()

            P4Thread = P4()
            P4Thread.connect()
            P4Thread.client = self.CurClient

            # 步骤1: sync -k 更新 have list
            self.UI.UpdateOperationLabel("正在更新文件索引...")
            self.UI.LogMessage("执行 sync -k 更新 have list...")
            try:
                RunSync(P4Thread, CmdTarget, FlushOnly=True)
                self.UI.LogMessage("have list 更新完成。")
            except P4Exception as Err:
                ErrStr = str(Err).lower()
                if "up-to-date" in ErrStr or "no file(s)" in ErrStr:
                    self.UI.LogMessage("have list 已是最新状态。")
                else:
                    raise

            if IsOffline:
                # 离线目录流程：使用 reconcile
                self.UI.UpdateOperationLabel("正在执行 reconcile...")
                self.UI.LogMessage("执行 reconcile 识别本地修改...")
                Result = RunReconcile(P4Thread, CmdTarget)
                Total = Result["edit"] + Result["add"] + Result["delete"]
                self.UI.LogMessage(f"reconcile 完成：{Result['edit']} 个修改，{Result['add']} 个新增，{Result['delete']} 个删除")
                if Total > 0:
                    self.UI.LogMessage("所有变更已放入默认 changelist，请在 P4V 中查看。")
                else:
                    self.UI.LogMessage("本地与服务器一致，无需处理。")
            else:
                # 普通目录流程：删除多余 + 同步差异
                # 步骤2: 解析 .p4ignore
                self.UI.UpdateOperationLabel("正在解析 .p4ignore...")
                self.UI.LogMessage("读取 .p4ignore 规则...")
                IgnoreParser = P4IgnoreParser(WorkspaceRoot)
                self.UI.LogMessage(f"已加载 {len(IgnoreParser.Patterns)} 条忽略规则。")

                # 步骤3: 获取 have list
                self.UI.UpdateOperationLabel("正在获取文件列表...")
                self.UI.LogMessage("获取 have list...")
                try:
                    HavePaths = GetHaveList(P4Thread, CmdTarget)
                    self.UI.LogMessage(f"have list 包含 {len(HavePaths)} 个文件。")
                except P4Exception as Err:
                    ErrStr = str(Err).lower()
                    if "no file(s)" in ErrStr:
                        HavePaths = set()
                        self.UI.LogMessage("have list 为空。")
                    else:
                        raise

                # 步骤4: 删除多余文件
                self.UI.UpdateOperationLabel("正在清理多余文件...")
                self.UI.LogMessage("检测并删除多余的版本控制文件...")
                DeletedCnt = DeleteObsoleteFiles(WorkspaceRoot, HavePaths, IgnoreParser, self.UI.LogMessage)
                self.UI.LogMessage(f"已删除 {DeletedCnt} 个多余文件。")

                # 步骤5: diff -se 覆盖内容不同的文件
                self.UI.UpdateOperationLabel("正在检测修改文件...")
                self.UI.LogMessage("执行 diff -se 检测内容不同的文件...")
                DiffFiles = GetDifferentFiles(P4Thread, CmdTarget)
                self.UI.LogMessage(f"发现 {len(DiffFiles)} 个内容不同的文件。")

                # 步骤6: diff -sd 下载缺失的文件
                self.UI.UpdateOperationLabel("正在检测缺失文件...")
                self.UI.LogMessage("执行 diff -sd 检测缺失的文件...")
                MissingFiles = GetMissingFiles(P4Thread, CmdTarget)
                self.UI.LogMessage(f"发现 {len(MissingFiles)} 个缺失的文件。")

                # 步骤7: 同步问题文件（先覆盖不同，再下载缺失）
                ProblemFiles = DiffFiles + MissingFiles
                if ProblemFiles:
                    self.UI.ShowProgressBar()
                    TotalFiles = len(ProblemFiles)

                    def OnFileProcessed(Cnt, DepotFile):
                        self.UI.UpdateProgress(Cnt, TotalFiles)
                        self.UI.LogMessage(DepotFile)

                    Handler = SyncOutputHandler(OnFileProcessed, self.UI.LogMessage)

                    self.UI.UpdateOperationLabel(f"正在同步 {TotalFiles} 个文件...")
                    self.UI.LogMessage(f"执行 sync -f --parallel 同步 {TotalFiles} 个文件...")
                    try:
                        SyncFiles(P4Thread, ProblemFiles, Handler, Parallel=8)
                        self.UI.LogMessage("文件同步完成。")
                    except P4Exception as Err:
                        ErrStr = str(Err).lower()
                        if "up-to-date" in ErrStr:
                            self.UI.LogMessage("文件已是最新状态。")
                        else:
                            self.UI.LogMessage(f"同步部分文件时出错：{Err}")
                else:
                    self.UI.LogMessage("所有文件已是最新状态。")

            self.UI.UpdateOperationLabel("操作已完成。")

        except P4Exception as Err:
            ErrMsgs = Err.errors if Err.errors else [str(Err)]
            self.UI.LogError("同步操作中发生错误：" + "\n".join(ErrMsgs))
            HasError = True
        except Exception as Err:
            self.UI.LogError(f"操作中发生错误：{Err}")
            HasError = True
        else:
            HasError = False
        finally:
            if P4Thread and P4Thread.connected():
                P4Thread.disconnect()
            self.FinishSyncAndClean(HasError)

    def FinishSyncAndClean(self, HasError: bool = False):
        """同步清理完成后的清理工作"""
        self.UI.HideProgressBar()
        self.UI.EnableUI()
        if HasError:
            self.UI.UpdateStatus("错误", "red")
            self.UI.LogError("操作完成，但有错误发生。")
        else:
            # 同步成功，清除 NeedSync 标记
            if self.SelectStreamPath:
                self.GlobalCfg.SetStreamNeedSync(self.SelectStreamPath, False)
            self.UI.UpdateStatus("就绪", "green")
            self.UI.LogMessage("操作已完成。")
            # 打开 P4V
            LaunchP4V(self.P4.port, self.P4.user, self.CurClient)
            self.UI.LogMessage("正在启动 P4V...")

    def UpdateWorkspaceFromCache(self):
        """根据工作区、缓存或默认值更新工作区目录和离线状态"""
        OfflineFlag = self.GlobalCfg.GetStreamOffline(self.SelectStreamPath)
        self.UI.OfflineVar.set(OfflineFlag)

        # 手动选择的目录不被自动覆盖
        if self.UI.WorkspaceIsManual:
            return

        # 构建目标工作区名称
        Tag = self.UI.WorkspaceTagVar.get().strip()
        Project = self.UI.P4ProjectVar.get()
        Stream = self.UI.P4StreamVar.get()
        TargetClientName = f"{Tag}_{Project}_{Stream}" if Tag else ""

        # 优先从已存在的工作区获取目录
        if TargetClientName and ClientExists(self.P4, TargetClientName):
            Root = GetClientRoot(self.P4, TargetClientName)
            if Root:
                self.UI.P4WorkspaceVar.set(Root)
                self.UI.SetWorkspaceSource(IsCached=True)
                # 更新缓存（保留 offline 和 need_sync）
                self.GlobalCfg.SetStreamCache(self.SelectStreamPath, Root)
                return

        # 其次从缓存获取
        Cached = self.GlobalCfg.GetStreamWorkspace(self.SelectStreamPath)
        if Cached:
            self.UI.P4WorkspaceVar.set(Cached)
            self.UI.SetWorkspaceSource(IsCached=True)
        else:
            # 最后使用默认路径
            DefaultPath = os.path.join(self.DefaultWorkspaceRoot, Project)
            self.UI.P4WorkspaceVar.set(DefaultPath)
            self.UI.SetWorkspaceSource(IsCached=False)
            self.UI.LogMessage(f"该流没有缓存记录，使用默认路径: {DefaultPath}")

    def UpdateWorkspacePreview(self):
        """更新工作区名称预览"""
        TagStr = self.UI.WorkspaceTagVar.get().strip() or "<标识>"
        ProjectStr = self.UI.P4ProjectVar.get() or "<项目>"
        StreamStr = self.UI.P4StreamVar.get() or "<分支>"
        Name = f"{TagStr}_{ProjectStr}_{StreamStr}"
        # 检查工作区是否存在
        try:
            Clients = GetAllClients(self.P4)
            Exists = any(Client.get('client') == Name for Client in Clients)
        except Exception:
            Exists = False
        self.UI.UpdateWorkspacePreview(Name, Exists)

    def UpdateUsedWorkspace(self):
        """更新使用工作区显示，只统计符合 标识_项目_分支 命名格式的工作区"""
        try:
            MaxCnt = max(1, self.UI.MaxWorkspaceCntVar.get())
        except Exception:
            MaxCnt = self.GlobalCfg.GetMaxWorkspaceCnt()

        Tag = self.UI.WorkspaceTagVar.get().strip()
        UsedCnt = 0
        if Tag:
            try:
                Clients = GetAllClients(self.P4)
                Prefix = f"{Tag}_"
                for Client in Clients:
                    Name = Client.get('client', '')
                    # 匹配 标识_项目_分支 格式（至少两个下划线分隔）
                    if Name.startswith(Prefix):
                        Parts = Name[len(Prefix):].split('_')
                        if len(Parts) >= 2:
                            UsedCnt += 1
            except Exception:
                pass
        self.UI.UpdateUsedWorkspace(UsedCnt, MaxCnt)

    def OnWorkspaceClick(self, event=None):
        """工作区目录点击事件，打开目录选择对话框"""
        CurPath = self.UI.P4WorkspaceVar.get()
        # 查找存在的目录作为初始目录
        InitialDir = self.FindExistingParent(CurPath)
        SelectedPath = filedialog.askdirectory(initialdir=InitialDir)
        if SelectedPath:
            self.UI.P4WorkspaceVar.set(SelectedPath)
            self.UI.SetWorkspaceSourceManual()

    def OnOfflineChanged(self):
        """离线复选框状态改变事件，保存到缓存"""
        if self.SelectStreamPath:
            self.GlobalCfg.SetStreamOffline(self.SelectStreamPath, self.UI.OfflineVar.get())

    def FindExistingParent(self, Path: str) -> str:
        """向上查找存在的父目录"""
        while Path:
            if os.path.isdir(Path):
                return Path
            Parent = os.path.dirname(Path)
            if Parent == Path:
                break
            Path = Parent
        return os.path.expanduser("~")

    def ResetDefaultVars(self):
        """重置默认变量"""
        self.UI.WorkspaceIsManual = False
        self.DefaultProject = self.UI.P4ProjectVar.get()
        self.DefaultStream = self.UI.P4StreamVar.get()

        ClientInfo = GetClientInfo(self.P4, self.CurClient)
        if ClientInfo:
            self.DefaultStreamPath = ClientInfo.get('Stream', '')
            WorkspaceRoot = ClientInfo.get('Root', '')
            self.DefaultWorkspaceRoot = os.path.dirname(WorkspaceRoot)

        self.UpdateWorkspaceFromCache()

    def Initialize(self, ClientName: str):
        """初始化回调状态"""
        self.CurClient = ClientName

        # 加载全局配置到 UI
        self.SavedTag = self.GlobalCfg.GetWorkspaceTag()
        self.UI.WorkspaceTagVar.set(self.SavedTag)
        self.UI.MaxWorkspaceCntVar.set(self.GlobalCfg.GetMaxWorkspaceCnt())
        self.UI.CreateP4ConfigVar.set(self.GlobalCfg.GetCreateP4Config())
        self.UI.AutoRmdirVar.set(self.GlobalCfg.GetAutoRmdir())
        self.UI.ServerUserVar.set(f"{self.P4.port} | {self.P4.user}")

        # 初始化客户端状态
        ClientInfo = GetClientInfo(self.P4, ClientName)
        if ClientInfo:
            self.SelectStreamPath = ClientInfo.get('Stream', '')
            Parsed = ParseStreamPath(self.SelectStreamPath)
            self.UI.P4ProjectVar.set(Parsed[0])
            self.UI.P4StreamVar.set(Parsed[1])

        self.ResetDefaultVars()
        self.UpdateWorkspacePreview()
        self.UpdateUsedWorkspace()
        self.OnTagVarChanged()  # 触发标识验证

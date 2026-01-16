import os
import threading
from tkinter import messagebox, filedialog
from P4 import P4, P4Exception

from Source.Data.P4Core import (
    GetLocalStreamClients, GetClientInfo, GetMainlineProjects,
    GetProjectStreams, ParseStreamPath, SwitchClientStream, GetAllStreams,
    GetOpenedFiles, GetHaveList, GetDifferentFiles, GetMissingFiles,
    SyncFiles, RunSync, P4IgnoreParser, DeleteObsoleteFiles, SyncOutputHandler,
    IsP4GUIRunning, RunReconcile, LaunchP4V, GetAllClients,
    CheckTagConflict, GetLocalClientsWithTag, RenameClient,
    CreateStreamClient, ClientExists, DeleteClient
)
from Source.Data.WorkspaceCache import WorkspaceCache, GlobalConfig
from Source.UI.UIComponents import AppUI


class AppCallbacks:
    """应用回调管理类"""

    def __init__(self, p4: P4, ui: AppUI):
        self.p4 = p4
        self.ui = ui

        # 全局配置
        self.global_config = GlobalConfig()

        # 状态变量
        self.select_stream_path = ""
        self.default_project = ""
        self.default_stream = ""
        self.default_workspace_root = ""
        self.default_stream_path = ""
        self.workspace_cache = None
        self.cur_client = ""
        self.saved_tag = ""  # 已保存的标识

        self._BindEvents()

    def _BindEvents(self):
        """绑定 UI 事件"""
        self.ui.project_combo.bind("<Button-1>", self.OnProjectDropdown)
        self.ui.project_combo.bind("<<ComboboxSelected>>", self.OnProjectSelected)
        self.ui.stream_combo.bind("<Button-1>", self.OnStreamDropdown)
        self.ui.stream_combo.bind("<<ComboboxSelected>>", self.OnStreamSelected)
        self.ui.apply_button.configure(command=self.OnApply)
        self.ui.workspace_entry.bind("<Button-1>", self.OnWorkspaceClick)
        self.ui.offline_checkbox.configure(command=self.OnOfflineChanged)
        # 通用配置事件
        self.ui.workspace_tag_var.trace_add("write", self._OnTagVarChanged)
        self.ui.tag_save_button.configure(command=self.OnTagSave)
        self.ui.max_workspace_spinbox.bind("<FocusOut>", self.OnMaxWorkspaceCntChanged)
        self.ui.max_workspace_cnt_var.trace_add("write", self._OnMaxCntVarChanged)

    def _OnTagVarChanged(self, *args):
        """工作区标识变量改变时验证标识并更新状态"""
        Tag = self.ui.workspace_tag_var.get().strip()
        self._UpdateWorkspacePreview()
        self._UpdateUsedWorkspace()

        # 空标识
        if not Tag:
            self.ui.SetTagStatus(False, Empty=True)
            return

        # 检查是否与其他主机冲突
        try:
            Conflicts = CheckTagConflict(self.p4, Tag)
            if Conflicts:
                self.ui.SetTagStatus(False)
                return
        except Exception:
            pass

        # 标识有效
        self.ui.SetTagStatus(True)

        # 如果标识与已保存的不同，启用保存按钮
        if Tag != self.saved_tag:
            self.ui.EnableTagSave(True)
        else:
            self.ui.EnableTagSave(False)

    def _OnMaxCntVarChanged(self, *args):
        """最大工作区数量变量改变时更新显示"""
        self._UpdateUsedWorkspace()

    def OnTagSave(self):
        """保存标识并重命名本地旧标识工作区"""
        NewTag = self.ui.workspace_tag_var.get().strip()
        OldTag = self.saved_tag

        if not NewTag:
            messagebox.showwarning("标识无效", "工作区标识不能为空")
            return

        # 检查冲突
        try:
            Conflicts = CheckTagConflict(self.p4, NewTag)
            if Conflicts:
                messagebox.showwarning("标识冲突", f"该标识已被其他主机使用：\n{', '.join(Conflicts[:5])}")
                return
        except Exception as e:
            messagebox.showerror("检查失败", f"检查标识时发生错误：{e}")
            return

        # 重命名旧标识的本地工作区
        if OldTag:
            try:
                OldClients = GetLocalClientsWithTag(self.p4, OldTag)
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
                                RenameClient(self.p4, OldName, NewName)
                                self.ui.LogMessage(f"已重命名: {OldName} -> {NewName}")
                            except Exception as e:
                                self.ui.LogMessage(f"重命名失败 {OldName}: {e}")
            except Exception as e:
                self.ui.LogMessage(f"获取旧工作区列表失败: {e}")

        # 保存配置
        self.global_config.SetWorkspaceTag(NewTag)
        self.saved_tag = NewTag
        self.ui.EnableTagSave(False)
        self.ui.LogMessage(f"工作区标识已保存: {NewTag}")
        self._UpdateWorkspacePreview()
        self._UpdateUsedWorkspace()

    def OnMaxWorkspaceCntChanged(self, event=None):
        """最大工作区数量改变，保存到缓存"""
        try:
            Cnt = self.ui.max_workspace_cnt_var.get()
            if Cnt < 1:
                Cnt = 1
                self.ui.max_workspace_cnt_var.set(Cnt)
            self.global_config.SetMaxWorkspaceCnt(Cnt)
            self._UpdateUsedWorkspace()
        except Exception:
            pass

    def OnProjectDropdown(self, event=None):
        """项目下拉框点击事件"""
        self.ui.project_combo['values'] = GetMainlineProjects(self.p4)

    def OnProjectSelected(self, event=None):
        """项目选择事件"""
        SelectProject = self.ui.p4_project_var.get()
        if SelectProject == self.default_project:
            self.ui.p4_stream_var.set(self.default_stream)
            self.select_stream_path = self.default_stream_path
        else:
            Streams = GetAllStreams(self.p4)
            for S in Streams:
                if S.get('Type') == 'mainline':
                    Parsed = ParseStreamPath(S.get('Stream', ''))
                    if Parsed[0] == SelectProject:
                        self.ui.p4_stream_var.set(Parsed[1])
                        self.select_stream_path = S.get('Stream', '')
                        break
        self._UpdateWorkspaceFromCache()
        self._UpdateWorkspacePreview()

    def OnStreamDropdown(self, event=None):
        """分支下拉框点击事件"""
        CurProject = self.ui.p4_project_var.get()
        self.ui.stream_combo['values'] = GetProjectStreams(self.p4, CurProject)

    def OnStreamSelected(self, event=None):
        """分支选择事件"""
        if not self.select_stream_path:
            return
        PathArray = self.select_stream_path.split('/')[-3:-1]
        if len(PathArray) >= 2:
            self.select_stream_path = f"//{PathArray[0]}/{PathArray[1]}/{self.ui.p4_stream_var.get()}"
        self._UpdateWorkspaceFromCache()
        self._UpdateWorkspacePreview()

    def OnApply(self):
        """一键切换按钮点击事件"""
        self.ui.ClearLog()

        # 检查工作区标识
        Tag = self.ui.workspace_tag_var.get().strip()
        if not Tag:
            messagebox.showwarning("缺少配置", "请先设置并保存工作区标识")
            return

        # 检查标识是否已保存
        if Tag != self.saved_tag:
            messagebox.showwarning("标识未保存", "请先保存工作区标识")
            return

        TargetWorkspace = self.ui.p4_workspace_var.get()
        Project = self.ui.p4_project_var.get()
        Stream = self.ui.p4_stream_var.get()
        TargetClientName = f"{Tag}_{Project}_{Stream}"
        MaxCnt = max(1, self.ui.max_workspace_cnt_var.get())

        # 检查是否使用默认路径，需要用户确认
        if self.ui.workspace_is_default:
            Result = messagebox.askyesno("确认默认路径",
                f"当前使用自动生成的默认路径：\n\n{TargetWorkspace}\n\n是否使用该路径？")
            if not Result:
                self.ui.LogMessage("用户取消操作。")
                return

        # 检查 P4V 是否运行中
        self.ui.LogMessage("正在检查 Perforce GUI 客户端...")
        if IsP4GUIRunning():
            messagebox.showwarning("无法切换", "检测到 P4V 正在运行中。\n\n请先关闭 P4V 后重试。")
            self.ui.LogMessage("检测到 P4V 运行中，操作已取消。")
            return

        # 检查目标工作区是否存在
        TargetExists = ClientExists(self.p4, TargetClientName)
        CurrentClients = GetLocalClientsWithTag(self.p4, Tag)
        CurrentCnt = len(CurrentClients)

        if TargetExists:
            # 目标工作区已存在，直接切换
            self.ui.LogMessage(f"目标工作区 {TargetClientName} 已存在，直接切换...")
        elif CurrentCnt < MaxCnt:
            # 未达上限，创建新工作区
            self.ui.LogMessage(f"创建新工作区 {TargetClientName}...")
        else:
            # 已达上限，需要删除最旧工作区
            OldestClient = self.global_config.GetOldestWorkspace(CurrentClients)
            if not OldestClient:
                messagebox.showerror("错误", "无法找到可删除的工作区")
                return

            self.ui.LogMessage(f"已达最大工作区数量 ({CurrentCnt}/{MaxCnt})，删除最旧工作区 {OldestClient}...")

            # 检查最旧工作区是否有未提交修改
            OpenedFiles = GetOpenedFiles(self.p4, OldestClient)
            if OpenedFiles:
                Cnt = len(OpenedFiles)
                Preview = "\n".join([F.get('depotFile', '') for F in OpenedFiles[:5] if isinstance(F, dict)])
                messagebox.showwarning("无法切换",
                    f"待删除的工作区 {OldestClient} 有 {Cnt} 个未提交文件：\n\n{Preview}\n\n请先提交或撤销修改。")
                self.ui.LogMessage(f"工作区 {OldestClient} 有未提交文件，操作已取消。")
                return

            # 删除旧工作区
            try:
                DeleteClient(self.p4, OldestClient)
                self.global_config.RemoveWorkspaceTimestamp(OldestClient)
                self.ui.LogMessage(f"已删除工作区: {OldestClient}")
            except Exception as E:
                messagebox.showerror("删除失败", f"删除工作区失败：{E}")
                return

        # 检查目录是否存在
        if not os.path.isdir(TargetWorkspace):
            Result = messagebox.askyesno("目录不存在",
                f"目录 {TargetWorkspace} 不存在。\n\n是否创建该目录并继续切换？")
            if not Result:
                self.ui.LogMessage("用户取消操作。")
                return
            os.makedirs(TargetWorkspace, exist_ok=True)
            self.ui.LogMessage(f"已创建目录: {TargetWorkspace}")

        # 创建或更新工作区配置
        self.ui.LogMessage(f"切换工作区: {TargetClientName}")
        self.ui.LogMessage(f"流路径: {self.select_stream_path}")
        self.ui.LogMessage(f"工作区目录: {TargetWorkspace}")

        if TargetExists:
            SwitchClientStream(self.p4, TargetClientName, self.select_stream_path, TargetWorkspace)
        else:
            CreateStreamClient(self.p4, TargetClientName, self.select_stream_path, TargetWorkspace)

        # 更新当前客户端和时间戳
        self.cur_client = TargetClientName
        self.p4.client = TargetClientName
        self.global_config.UpdateWorkspaceTimestamp(TargetClientName)

        # 保存工作区目录和离线标记到缓存
        IsOffline = self.ui.offline_var.get()
        if self.workspace_cache:
            self.workspace_cache.Set(self.select_stream_path, TargetWorkspace, IsOffline)

        self._ResetDefaultVars()
        self._UpdateUsedWorkspace()

        self.ui.UpdateStatus("正在同步...", "orange", Blink=True)
        self.ui.DisableUI()
        threading.Thread(target=self._RunSyncAndClean, args=(IsOffline,), daemon=True).start()

    def _RunSyncAndClean(self, IsOffline: bool = False):
        """执行同步和清理操作"""
        P4Thread = None
        try:
            self.ui.UpdateOperationLabel("正在连接服务器...")
            CmdTarget = f"//{self.cur_client}/..."
            WorkspaceRoot = self.ui.p4_workspace_var.get()

            P4Thread = P4()
            P4Thread.connect()
            P4Thread.client = self.cur_client

            # 步骤1: sync -k 更新 have list
            self.ui.UpdateOperationLabel("正在更新文件索引...")
            self.ui.LogMessage("执行 sync -k 更新 have list...")
            try:
                RunSync(P4Thread, CmdTarget, flush_only=True)
                self.ui.LogMessage("have list 更新完成。")
            except P4Exception as E:
                ErrStr = str(E).lower()
                if "up-to-date" in ErrStr or "no file(s)" in ErrStr:
                    self.ui.LogMessage("have list 已是最新状态。")
                else:
                    raise

            if IsOffline:
                # 离线目录流程：使用 reconcile
                self.ui.UpdateOperationLabel("正在执行 reconcile...")
                self.ui.LogMessage("执行 reconcile 识别本地修改...")
                Result = RunReconcile(P4Thread, CmdTarget)
                Total = Result["edit"] + Result["add"] + Result["delete"]
                self.ui.LogMessage(f"reconcile 完成：{Result['edit']} 个修改，{Result['add']} 个新增，{Result['delete']} 个删除")
                if Total > 0:
                    self.ui.LogMessage("所有变更已放入默认 changelist，请在 P4V 中查看。")
                else:
                    self.ui.LogMessage("本地与服务器一致，无需处理。")
            else:
                # 普通目录流程：删除多余 + 同步差异
                # 步骤2: 解析 .p4ignore
                self.ui.UpdateOperationLabel("正在解析 .p4ignore...")
                self.ui.LogMessage("读取 .p4ignore 规则...")
                IgnoreParser = P4IgnoreParser(WorkspaceRoot)
                self.ui.LogMessage(f"已加载 {len(IgnoreParser.patterns)} 条忽略规则。")

                # 步骤3: 获取 have list
                self.ui.UpdateOperationLabel("正在获取文件列表...")
                self.ui.LogMessage("获取 have list...")
                try:
                    HavePaths = GetHaveList(P4Thread, CmdTarget)
                    self.ui.LogMessage(f"have list 包含 {len(HavePaths)} 个文件。")
                except P4Exception as E:
                    ErrStr = str(E).lower()
                    if "no file(s)" in ErrStr:
                        HavePaths = set()
                        self.ui.LogMessage("have list 为空。")
                    else:
                        raise

                # 步骤4: 删除多余文件
                self.ui.UpdateOperationLabel("正在清理多余文件...")
                self.ui.LogMessage("检测并删除多余的版本控制文件...")
                DeletedCnt = DeleteObsoleteFiles(WorkspaceRoot, HavePaths, IgnoreParser, self.ui.LogMessage)
                self.ui.LogMessage(f"已删除 {DeletedCnt} 个多余文件。")

                # 步骤5: diff -se 覆盖内容不同的文件
                self.ui.UpdateOperationLabel("正在检测修改文件...")
                self.ui.LogMessage("执行 diff -se 检测内容不同的文件...")
                DiffFiles = GetDifferentFiles(P4Thread, CmdTarget)
                self.ui.LogMessage(f"发现 {len(DiffFiles)} 个内容不同的文件。")

                # 步骤6: diff -sd 下载缺失的文件
                self.ui.UpdateOperationLabel("正在检测缺失文件...")
                self.ui.LogMessage("执行 diff -sd 检测缺失的文件...")
                MissingFiles = GetMissingFiles(P4Thread, CmdTarget)
                self.ui.LogMessage(f"发现 {len(MissingFiles)} 个缺失的文件。")

                # 步骤7: 同步问题文件（先覆盖不同，再下载缺失）
                ProblemFiles = DiffFiles + MissingFiles
                if ProblemFiles:
                    self.ui.ShowProgressBar()
                    TotalFiles = len(ProblemFiles)

                    def OnFileProcessed(Cnt, DepotFile):
                        self.ui.UpdateProgress(Cnt, TotalFiles)
                        self.ui.LogMessage(DepotFile)

                    Handler = SyncOutputHandler(OnFileProcessed, self.ui.LogMessage)

                    self.ui.UpdateOperationLabel(f"正在同步 {TotalFiles} 个文件...")
                    self.ui.LogMessage(f"执行 sync -f --parallel 同步 {TotalFiles} 个文件...")
                    try:
                        SyncFiles(P4Thread, ProblemFiles, Handler, parallel=8)
                        self.ui.LogMessage("文件同步完成。")
                    except P4Exception as E:
                        ErrStr = str(E).lower()
                        if "up-to-date" in ErrStr:
                            self.ui.LogMessage("文件已是最新状态。")
                        else:
                            self.ui.LogMessage(f"同步部分文件时出错：{E}")
                else:
                    self.ui.LogMessage("所有文件已是最新状态。")

            self.ui.UpdateOperationLabel("操作已完成。")

        except P4Exception as E:
            self.ui.LogMessage("同步操作中发生错误：" + "\n".join(E.errors))
            HasError = True
        except Exception as E:
            self.ui.LogMessage(f"操作中发生错误：{E}")
            HasError = True
        else:
            HasError = False
        finally:
            if P4Thread and P4Thread.connected():
                P4Thread.disconnect()
            self._FinishSyncAndClean(HasError)

    def _FinishSyncAndClean(self, HasError: bool = False):
        """同步清理完成后的清理工作"""
        self.ui.HideProgressBar()
        self.ui.EnableUI()
        if HasError:
            self.ui.UpdateStatus("错误", "red")
            self.ui.LogMessage("操作完成，但有错误发生。")
        else:
            self.ui.UpdateStatus("就绪", "green")
            self.ui.LogMessage("操作已完成。")
            # 打开 P4V
            LaunchP4V(self.p4.port, self.p4.user, self.cur_client)
            self.ui.LogMessage("正在启动 P4V...")

    def _UpdateWorkspaceFromCache(self):
        """根据缓存或默认值更新工作区目录和离线状态"""
        Cached = self.workspace_cache.Get(self.select_stream_path) if self.workspace_cache else None
        OfflineFlag = self.workspace_cache.GetOffline(self.select_stream_path) if self.workspace_cache else False

        self.ui.offline_var.set(OfflineFlag)

        if Cached:
            self.ui.p4_workspace_var.set(Cached)
            self.ui.SetWorkspaceSource(is_cached=True)
        else:
            DefaultPath = os.path.join(self.default_workspace_root, self.ui.p4_project_var.get())
            self.ui.p4_workspace_var.set(DefaultPath)
            self.ui.SetWorkspaceSource(is_cached=False)
            self.ui.LogMessage(f"该流没有缓存记录，使用默认路径: {DefaultPath}")

    def _UpdateWorkspacePreview(self):
        """更新工作区名称预览"""
        TagStr = self.ui.workspace_tag_var.get().strip() or "<标识>"
        ProjectStr = self.ui.p4_project_var.get() or "<项目>"
        StreamStr = self.ui.p4_stream_var.get() or "<分支>"
        Name = f"{TagStr}_{ProjectStr}_{StreamStr}"
        # 检查工作区是否存在
        try:
            Clients = GetAllClients(self.p4)
            Exists = any(C.get('client') == Name for C in Clients)
        except Exception:
            Exists = False
        self.ui.UpdateWorkspacePreview(Name, Exists)

    def _UpdateUsedWorkspace(self):
        """更新使用工作区显示，只统计符合 标识_项目_分支 命名格式的工作区"""
        try:
            MaxCnt = max(1, self.ui.max_workspace_cnt_var.get())
        except Exception:
            MaxCnt = self.global_config.GetMaxWorkspaceCnt()

        Tag = self.ui.workspace_tag_var.get().strip()
        UsedCnt = 0
        if Tag:
            try:
                Clients = GetAllClients(self.p4)
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
        self.ui.UpdateUsedWorkspace(UsedCnt, MaxCnt)

    def OnWorkspaceClick(self, event=None):
        """工作区目录点击事件，打开目录选择对话框"""
        CurPath = self.ui.p4_workspace_var.get()
        # 查找存在的目录作为初始目录
        InitialDir = self._FindExistingParent(CurPath)
        SelectedPath = filedialog.askdirectory(initialdir=InitialDir)
        if SelectedPath:
            self.ui.p4_workspace_var.set(SelectedPath)
            self.ui.SetWorkspaceSourceManual()

    def OnOfflineChanged(self):
        """离线复选框状态改变事件，保存到缓存"""
        if self.workspace_cache and self.select_stream_path:
            self.workspace_cache.SetOffline(self.select_stream_path, self.ui.offline_var.get())

    def _FindExistingParent(self, Path: str) -> str:
        """向上查找存在的父目录"""
        while Path:
            if os.path.isdir(Path):
                return Path
            Parent = os.path.dirname(Path)
            if Parent == Path:
                break
            Path = Parent
        return os.path.expanduser("~")

    def _ResetDefaultVars(self):
        """重置默认变量"""
        self.default_project = self.ui.p4_project_var.get()
        self.default_stream = self.ui.p4_stream_var.get()

        ClientInfo = GetClientInfo(self.p4, self.cur_client)
        if ClientInfo:
            self.default_stream_path = ClientInfo.get('Stream', '')
            WorkspaceRoot = ClientInfo.get('Root', '')
            WorkspaceArray = WorkspaceRoot.split('\\')[:-1]
            if len(WorkspaceArray) > 1:
                WorkspaceArray.insert(1, '\\')
                self.default_workspace_root = os.path.join(*WorkspaceArray)
            else:
                self.default_workspace_root = WorkspaceRoot

        self._UpdateWorkspaceFromCache()

    def Initialize(self, client_name: str):
        """初始化回调状态"""
        self.cur_client = client_name
        self.workspace_cache = WorkspaceCache(client_name)

        # 加载全局配置到 UI
        self.saved_tag = self.global_config.GetWorkspaceTag()
        self.ui.workspace_tag_var.set(self.saved_tag)
        self.ui.max_workspace_cnt_var.set(self.global_config.GetMaxWorkspaceCnt())
        self.ui.server_user_var.set(f"{self.p4.port} | {self.p4.user}")

        # 初始化客户端状态
        ClientInfo = GetClientInfo(self.p4, client_name)
        if ClientInfo:
            self.select_stream_path = ClientInfo.get('Stream', '')
            Parsed = ParseStreamPath(self.select_stream_path)
            self.ui.p4_project_var.set(Parsed[0])
            self.ui.p4_stream_var.set(Parsed[1])

        self._ResetDefaultVars()
        self._UpdateWorkspacePreview()
        self._UpdateUsedWorkspace()
        self._OnTagVarChanged()  # 触发标识验证

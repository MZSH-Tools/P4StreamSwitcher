import os
import threading
from tkinter import messagebox, filedialog
from P4 import P4, P4Exception

from Source.Data.P4Core import (
    GetLocalStreamClients, GetClientInfo, GetMainlineProjects,
    GetProjectStreams, ParseStreamPath, SwitchClientStream, GetAllStreams,
    GetOpenedFiles, GetHaveList, GetDifferentFiles, GetMissingFiles,
    SyncFiles, RunSync, P4IgnoreParser, DeleteObsoleteFiles, SyncOutputHandler,
    IsP4GUIRunning
)
from Source.Data.WorkspaceCache import WorkspaceCache
from Source.UI.UIComponents import AppUI


class AppCallbacks:
    """应用回调管理类"""

    def __init__(self, p4: P4, ui: AppUI):
        self.p4 = p4
        self.ui = ui

        # 状态变量
        self.select_stream_path = ""
        self.default_project = ""
        self.default_stream = ""
        self.default_workspace_root = ""
        self.default_stream_path = ""
        self.workspace_cache = None

        self._BindEvents()

    def _BindEvents(self):
        """绑定 UI 事件"""
        self.ui.client_combo.bind("<Button-1>", self.OnClientDropdown)
        self.ui.client_combo.bind("<<ComboboxSelected>>", self.OnClientSelected)
        self.ui.project_combo.bind("<Button-1>", self.OnProjectDropdown)
        self.ui.project_combo.bind("<<ComboboxSelected>>", self.OnProjectSelected)
        self.ui.stream_combo.bind("<Button-1>", self.OnStreamDropdown)
        self.ui.stream_combo.bind("<<ComboboxSelected>>", self.OnStreamSelected)
        self.ui.apply_button.configure(command=self.OnApply)
        self.ui.workspace_entry.bind("<Button-1>", self.OnWorkspaceClick)

    def OnClientDropdown(self, event=None):
        """客户端下拉框点击事件"""
        self.ui.client_combo['values'] = GetLocalStreamClients(self.p4)

    def OnClientSelected(self, event=None):
        """客户端选择事件"""
        cur_client = self.ui.p4_client_var.get()
        # 加载该客户端的缓存
        self.workspace_cache = WorkspaceCache(cur_client)
        client_info = GetClientInfo(self.p4, cur_client)
        if client_info:
            self.select_stream_path = client_info.get('Stream', '')
            parsed = ParseStreamPath(self.select_stream_path)
            self.ui.p4_project_var.set(parsed[0])
            self.ui.p4_stream_var.set(parsed[1])
        self._ResetDefaultVars()

    def OnProjectDropdown(self, event=None):
        """项目下拉框点击事件"""
        self.ui.project_combo['values'] = GetMainlineProjects(self.p4)

    def OnProjectSelected(self, event=None):
        """项目选择事件"""
        select_project = self.ui.p4_project_var.get()
        if select_project == self.default_project:
            self.ui.p4_stream_var.set(self.default_stream)
            self.select_stream_path = self.default_stream_path
        else:
            streams = GetAllStreams(self.p4)
            for stream in streams:
                if stream.get('Type') == 'mainline':
                    parsed = ParseStreamPath(stream.get('Stream', ''))
                    if parsed[0] == select_project:
                        self.ui.p4_stream_var.set(parsed[1])
                        self.select_stream_path = stream.get('Stream', '')
                        break
        self._UpdateWorkspaceFromCache()

    def OnStreamDropdown(self, event=None):
        """分支下拉框点击事件"""
        cur_project = self.ui.p4_project_var.get()
        self.ui.stream_combo['values'] = GetProjectStreams(self.p4, cur_project)

    def OnStreamSelected(self, event=None):
        """分支选择事件"""
        if not self.select_stream_path:
            return
        path_array = self.select_stream_path.split('/')[-3:-1]
        if len(path_array) >= 2:
            self.select_stream_path = f"//{path_array[0]}/{path_array[1]}/{self.ui.p4_stream_var.get()}"
        self._UpdateWorkspaceFromCache()

    def OnApply(self):
        """一键切换按钮点击事件"""
        self.ui.ClearLog()

        target_workspace = self.ui.p4_workspace_var.get()
        client_name = self.ui.p4_client_var.get()

        # 检查未提交的修改
        self.ui.LogMessage("正在检查未提交的修改...")
        opened_files = GetOpenedFiles(self.p4, client_name)
        if opened_files:
            count = len(opened_files)
            files_preview = "\n".join([f.get('depotFile', '') for f in opened_files[:5] if isinstance(f, dict)])
            messagebox.showwarning("无法切换", f"检测到 {count} 个未提交的文件，请先提交或撤销修改后再切换。\n\n{files_preview}")
            self.ui.LogMessage(f"检测到 {count} 个未提交文件，操作已取消。")
            return

        # 检查 P4V 是否运行中
        self.ui.LogMessage("正在检查 Perforce GUI 客户端...")
        if IsP4GUIRunning():
            messagebox.showwarning("无法切换", "检测到 P4V 正在运行中。\n\n切换工作区时运行 P4V 可能导致未知错误，请先关闭 P4V 后重试。")
            self.ui.LogMessage("检测到 P4V 运行中，操作已取消。")
            return

        # 检查目录是否存在
        if not os.path.isdir(target_workspace):
            result = messagebox.askyesno("目录不存在",
                f"目录 {target_workspace} 不存在。\n\n是否创建该目录并继续切换？")
            if not result:
                self.ui.LogMessage("用户取消操作。")
                return
            os.makedirs(target_workspace, exist_ok=True)
            self.ui.LogMessage(f"已创建目录: {target_workspace}")

        self.ui.LogMessage("检查通过，开始切换...")
        self.ui.LogMessage(f"切换客户端为：{client_name}")
        self.ui.LogMessage(f"切换流路径：{self.select_stream_path}")
        self.ui.LogMessage(f"切换工作区路径：{target_workspace}")

        SwitchClientStream(self.p4, client_name, self.select_stream_path, target_workspace)

        # 保存工作区目录到缓存
        if self.workspace_cache:
            self.workspace_cache.Set(self.select_stream_path, target_workspace)

        self._ResetDefaultVars()

        self.ui.DisableUI()
        threading.Thread(target=self._RunSyncAndClean, daemon=True).start()

    def _RunSyncAndClean(self):
        """执行同步和清理操作"""
        p4_thread = None
        try:
            self.ui.UpdateOperationLabel("正在连接服务器...")
            command_target = f"//{self.ui.p4_client_var.get()}/..."
            workspace_root = self.ui.p4_workspace_var.get()

            p4_thread = P4()
            p4_thread.connect()
            p4_thread.client = self.ui.p4_client_var.get()

            # 步骤1: sync -k 更新 have list
            self.ui.UpdateOperationLabel("正在更新文件索引...")
            self.ui.LogMessage("执行 sync -k 更新 have list...")
            RunSync(p4_thread, command_target, flush_only=True)
            self.ui.LogMessage("have list 更新完成。")

            # 步骤2: 解析 .p4ignore
            self.ui.UpdateOperationLabel("正在解析 .p4ignore...")
            self.ui.LogMessage("读取 .p4ignore 规则...")
            ignore_parser = P4IgnoreParser(workspace_root)
            self.ui.LogMessage(f"已加载 {len(ignore_parser.patterns)} 条忽略规则。")

            # 步骤3: 获取 have list
            self.ui.UpdateOperationLabel("正在获取文件列表...")
            self.ui.LogMessage("获取 have list...")
            have_paths = GetHaveList(p4_thread, command_target)
            self.ui.LogMessage(f"have list 包含 {len(have_paths)} 个文件。")

            # 步骤4: 删除多余文件
            self.ui.UpdateOperationLabel("正在清理多余文件...")
            self.ui.LogMessage("检测并删除多余的版本控制文件...")
            deleted_count = DeleteObsoleteFiles(workspace_root, have_paths, ignore_parser, self.ui.LogMessage)
            self.ui.LogMessage(f"已删除 {deleted_count} 个多余文件。")

            # 步骤5: diff -se 覆盖内容不同的文件
            self.ui.UpdateOperationLabel("正在检测修改文件...")
            self.ui.LogMessage("执行 diff -se 检测内容不同的文件...")
            different_files = GetDifferentFiles(p4_thread, command_target)
            self.ui.LogMessage(f"发现 {len(different_files)} 个内容不同的文件。")

            # 步骤6: diff -sd 下载缺失的文件
            self.ui.UpdateOperationLabel("正在检测缺失文件...")
            self.ui.LogMessage("执行 diff -sd 检测缺失的文件...")
            missing_files = GetMissingFiles(p4_thread, command_target)
            self.ui.LogMessage(f"发现 {len(missing_files)} 个缺失的文件。")

            # 步骤7: 同步问题文件（先覆盖不同，再下载缺失）
            problem_files = different_files + missing_files
            if problem_files:
                self.ui.ShowProgressBar()
                total_files = len(problem_files)

                def on_file_processed(count, depot_file):
                    self.ui.UpdateProgress(count, total_files)
                    self.ui.LogMessage(depot_file)

                handler = SyncOutputHandler(on_file_processed, self.ui.LogMessage)

                self.ui.UpdateOperationLabel(f"正在同步 {total_files} 个文件...")
                self.ui.LogMessage(f"执行 sync -f --parallel 同步 {total_files} 个文件...")
                SyncFiles(p4_thread, problem_files, handler, parallel=4)
                self.ui.LogMessage("文件同步完成。")
            else:
                self.ui.LogMessage("所有文件已是最新状态。")

            self.ui.UpdateOperationLabel("操作已完成。")

        except P4Exception as e:
            err_str = str(e)
            if "up-to-date" in err_str or "no file(s)" in err_str:
                self.ui.LogMessage("文件已经是最新状态。")
            else:
                self.ui.LogMessage("同步操作中发生错误：" + "\n".join(e.errors))
        except Exception as e:
            self.ui.LogMessage(f"操作中发生错误：{e}")
        finally:
            if p4_thread and p4_thread.connected():
                p4_thread.disconnect()
            self._FinishSyncAndClean()

    def _FinishSyncAndClean(self):
        """同步清理完成后的清理工作"""
        self.ui.LogMessage("操作已完成。")
        self.ui.HideProgressBar()
        self.ui.EnableUI()

    def _UpdateWorkspaceFromCache(self):
        """根据缓存或默认值更新工作区目录"""
        cached = self.workspace_cache.Get(self.select_stream_path) if self.workspace_cache else None

        if cached:
            self.ui.p4_workspace_var.set(cached)
            exists = os.path.isdir(cached)
            self.ui.SetWorkspaceSource(is_cached=True)
        else:
            default_path = os.path.join(self.default_workspace_root, self.ui.p4_project_var.get())
            self.ui.p4_workspace_var.set(default_path)
            exists = os.path.isdir(default_path)
            self.ui.SetWorkspaceSource(is_cached=False)
            self.ui.LogMessage(f"该流没有缓存记录，使用默认路径: {default_path}")

        self.ui.SetWorkspaceState(exists)

    def OnWorkspaceClick(self, event=None):
        """工作区目录点击事件，打开目录选择对话框"""
        cur_path = self.ui.p4_workspace_var.get()
        # 查找存在的目录作为初始目录
        initial_dir = self._FindExistingParent(cur_path)
        path = filedialog.askdirectory(initialdir=initial_dir)
        if path:
            self.ui.p4_workspace_var.set(path)
            self.ui.SetWorkspaceSourceManual()
            self.ui.SetWorkspaceState(True)

    def _FindExistingParent(self, path: str) -> str:
        """向上查找存在的父目录"""
        while path:
            if os.path.isdir(path):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        return os.path.expanduser("~")

    def _ResetDefaultVars(self):
        """重置默认变量"""
        self.default_project = self.ui.p4_project_var.get()
        self.default_stream = self.ui.p4_stream_var.get()

        cur_client = self.ui.p4_client_var.get()
        client_info = GetClientInfo(self.p4, cur_client)
        if client_info:
            self.default_stream_path = client_info.get('Stream', '')
            workspace_root = client_info.get('Root', '')
            workspace_array = workspace_root.split('\\')[:-1]
            if len(workspace_array) > 1:
                workspace_array.insert(1, '\\')
                self.default_workspace_root = os.path.join(*workspace_array)
            else:
                self.default_workspace_root = workspace_root

        self._UpdateWorkspaceFromCache()

    def Initialize(self):
        """初始化回调状态"""
        self.OnClientSelected()

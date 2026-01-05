import os
import threading
from P4 import P4, P4Exception

from Source.Data.P4Core import (
    GetLocalStreamClients, GetClientInfo, GetMainlineProjects,
    GetProjectStreams, ParseStreamPath, SwitchClientStream,
    CountSyncFiles, CountCleanFiles, RunSync, RunClean, GetAllStreams,
    SyncOutputHandler
)
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

    def OnClientDropdown(self, event=None):
        """客户端下拉框点击事件"""
        self.ui.client_combo['values'] = GetLocalStreamClients(self.p4)

    def OnClientSelected(self, event=None):
        """客户端选择事件"""
        cur_client = self.ui.p4_client_var.get()
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
        self._UpdateWorkspaceText()

    def OnStreamDropdown(self, event=None):
        """分支下拉框点击事件"""
        cur_project = self.ui.p4_project_var.get()
        self.ui.stream_combo['values'] = GetProjectStreams(self.p4, cur_project)

    def OnStreamSelected(self, event=None):
        """分支选择事件"""
        path_array = self.select_stream_path.split('/')[-3:-1]
        self.select_stream_path = f"//{path_array[0]}/{path_array[1]}/{self.ui.p4_stream_var.get()}"

    def OnApply(self):
        """一键应用按钮点击事件"""
        self.ui.ClearLog()

        target_workspace = self.ui.p4_workspace_var.get()
        client_name = self.ui.p4_client_var.get()

        self.ui.LogMessage(f"切换客户端为：{client_name}")
        self.ui.LogMessage(f"切换流路径：{self.select_stream_path}")
        self.ui.LogMessage(f"切换工作区路径：{target_workspace}")

        SwitchClientStream(self.p4, client_name, self.select_stream_path, target_workspace)
        self._ResetDefaultVars()

        self.ui.DisableUI()
        threading.Thread(target=self._RunSyncAndClean, daemon=True).start()

    def _RunSyncAndClean(self):
        """执行同步和清理操作"""
        p4_thread = None
        try:
            self.ui.UpdateOperationLabel("正在连接服务器...")
            command_target = f"//{self.ui.p4_client_var.get()}/..."

            p4_thread = P4()
            p4_thread.connect()

            total_files = 0

            if self.ui.auto_sync_var.get():
                total_files += CountSyncFiles(p4_thread, command_target)

            if self.ui.auto_clean_var.get():
                total_files += CountCleanFiles(p4_thread, command_target)

            if total_files == 0:
                total_files = 1

            self.ui.ShowProgressBar()

            def on_file_processed(processed, depot_file):
                self.ui.UpdateProgress(processed, total_files)
                self.ui.LogMessage(depot_file)

            handler = SyncOutputHandler(on_file_processed, self.ui.LogMessage)

            if self.ui.auto_sync_var.get():
                self.ui.UpdateOperationLabel("正在链接文件...")
                self.ui.LogMessage("开始执行 sync -k 命令...")
                RunSync(p4_thread, command_target, handler)
                self.ui.LogMessage("sync -k 命令已完成，文件状态更新完成。")

            if self.ui.auto_clean_var.get():
                self.ui.UpdateOperationLabel("正在清理工作区...")
                self.ui.LogMessage("开始执行 clean 命令...")
                RunClean(p4_thread, command_target, handler)
                self.ui.LogMessage("clean 命令已完成，工作区已清理。")

            self.ui.UpdateOperationLabel("操作已完成。")

        except P4Exception as e:
            if "up-to-date" in str(e) or "no file(s) to reconcile" in str(e):
                self.ui.LogMessage("文件已经是最新状态。")
            else:
                self.ui.LogMessage("同步操作中发生错误：" + "\n".join(e.errors))
        finally:
            if p4_thread and p4_thread.connected():
                p4_thread.disconnect()
            self._FinishSyncAndClean()

    def _FinishSyncAndClean(self):
        """同步清理完成后的清理工作"""
        self.ui.LogMessage("操作已完成。")
        self.ui.HideProgressBar()
        self.ui.EnableUI()

    def _UpdateWorkspaceText(self):
        """更新工作区目录显示"""
        self.ui.p4_workspace_var.set(os.path.join(self.default_workspace_root, self.ui.p4_project_var.get()))

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

        self._UpdateWorkspaceText()

    def Initialize(self):
        """初始化回调状态"""
        self.OnClientSelected()

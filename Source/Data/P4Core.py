from P4 import P4, P4Exception, OutputHandler
import socket


def GetLocalStreamClients(p4: P4):
    """获取本地主机上当前用户的所有流客户端"""
    local_hostname = socket.gethostname()
    clients = p4.run_clients()
    local_stream_clients = []
    for client in clients:
        client_host = client.get('Host', '')
        client_user = client.get('Owner', '')
        if client_host.lower() == local_hostname.lower() and client_user == p4.user and 'Stream' in client:
            local_stream_clients.append(client.get('client', p4.client))
    return local_stream_clients


def GetAllStreams(p4: P4):
    """获取所有流"""
    return p4.run_streams()


def GetAllClients(p4: P4):
    """获取所有客户端"""
    return p4.run_clients()


def GetMainlineProjects(p4: P4):
    """获取所有主线类型的流项目"""
    streams = p4.run_streams()
    projects = []
    for stream in streams:
        if stream.get('Type', '') == 'mainline':
            parsed = ParseStreamPath(stream.get('Stream', ''))
            projects.append(parsed[0])
    return projects


def GetProjectStreams(p4: P4, project_name: str):
    """获取指定项目下的所有流分支"""
    streams = p4.run_streams()
    values = []
    for stream in streams:
        parsed = ParseStreamPath(stream.get('Stream', ''))
        if parsed[0] == project_name:
            values.append(parsed[1])
    return values


def ParseStreamPath(stream_path: str):
    """解析流路径，返回 [项目名, 分支名]"""
    return stream_path.split('/')[-2:]


def GetClientInfo(p4: P4, client_name: str):
    """获取客户端信息"""
    for client in p4.run_clients():
        if client.get('client', '') == client_name:
            return client
    return None


def SwitchClientStream(p4: P4, client_name: str, stream_path: str, workspace_root: str):
    """切换客户端的流和工作区"""
    p4.client = client_name
    client_spec = p4.fetch_client()
    client_spec["Stream"] = stream_path
    client_spec["Root"] = workspace_root
    p4.save_client(client_spec)


class PreviewOutputHandler(OutputHandler):
    """用于统计文件数量的 Handler"""
    def __init__(self):
        super().__init__()
        self.count = 0

    def outputStat(self, stat):
        self.count += 1
        return OutputHandler.HANDLED


class SyncOutputHandler(OutputHandler):
    """用于同步操作的 Handler，支持进度回调"""
    def __init__(self, on_file_processed=None, on_text=None):
        super().__init__()
        self.processed_files = 0
        self.on_file_processed = on_file_processed
        self.on_text = on_text

    def outputStat(self, stat):
        self.processed_files += 1
        if self.on_file_processed:
            self.on_file_processed(self.processed_files, stat.get('depotFile', ''))
        return OutputHandler.HANDLED

    def outputText(self, text):
        if self.on_text:
            self.on_text(text)
        return OutputHandler.HANDLED

    def outputInfo(self, info):
        if self.on_text:
            self.on_text(info)
        return OutputHandler.HANDLED


def CountSyncFiles(p4: P4, command_target: str):
    """统计 sync 命令将处理的文件数"""
    handler = PreviewOutputHandler()
    p4.handler = handler
    p4.run("sync", "-k", "-n", command_target)
    return handler.count


def CountCleanFiles(p4: P4, command_target: str):
    """统计 clean 命令将处理的文件数"""
    handler = PreviewOutputHandler()
    p4.handler = handler
    p4.run("clean", "-n", command_target)
    return handler.count


def RunSync(p4: P4, command_target: str, handler: OutputHandler = None):
    """执行 sync -k 命令"""
    if handler:
        p4.handler = handler
    p4.run("sync", "-k", command_target)


def RunClean(p4: P4, command_target: str, handler: OutputHandler = None):
    """执行 clean 命令"""
    if handler:
        p4.handler = handler
    p4.run("clean", command_target)

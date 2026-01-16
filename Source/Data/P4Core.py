from P4 import P4, P4Exception, OutputHandler
import socket
import os
import stat
import fnmatch
import subprocess
import platform


def IsP4GUIRunning() -> bool:
    """检测 P4V 是否正在运行"""
    try:
        if platform.system() == 'Windows':
            output = subprocess.check_output(['tasklist'], universal_newlines=True)
            return 'p4v.exe' in output.lower()
        else:
            output = subprocess.check_output(['pgrep', '-x', 'p4v'], stderr=subprocess.DEVNULL)
            return bool(output.strip())
    except Exception:
        return False


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


def CheckTagConflict(p4: P4, Tag: str) -> list:
    """检查标识是否被其他主机使用，返回冲突的客户端列表"""
    if not Tag:
        return []
    LocalHost = socket.gethostname().lower()
    Prefix = f"{Tag}_"
    Conflicts = []
    for Client in p4.run_clients():
        Name = Client.get('client', '')
        Host = Client.get('Host', '').lower()
        # 匹配 标识_项目_分支 格式
        if Name.startswith(Prefix):
            Parts = Name[len(Prefix):].split('_')
            if len(Parts) >= 2 and Host != LocalHost:
                Conflicts.append(Name)
    return Conflicts


def GetLocalClientsWithTag(p4: P4, Tag: str) -> list:
    """获取本地使用指定标识的客户端列表"""
    if not Tag:
        return []
    LocalHost = socket.gethostname().lower()
    Prefix = f"{Tag}_"
    Clients = []
    for Client in p4.run_clients():
        Name = Client.get('client', '')
        Host = Client.get('Host', '').lower()
        Owner = Client.get('Owner', '')
        # 匹配 标识_项目_分支 格式，本地且属于当前用户
        if Name.startswith(Prefix) and Host == LocalHost and Owner == p4.user:
            Parts = Name[len(Prefix):].split('_')
            if len(Parts) >= 2:
                Clients.append(Name)
    return Clients


def RenameClient(p4: P4, OldName: str, NewName: str):
    """重命名客户端"""
    # 获取旧客户端配置
    p4.client = OldName
    OldSpec = p4.fetch_client()

    # 创建新客户端
    p4.client = NewName
    NewSpec = p4.fetch_client()
    for Key in ['Root', 'Stream', 'Options', 'SubmitOptions', 'LineEnd']:
        if Key in OldSpec:
            NewSpec[Key] = OldSpec[Key]
    p4.save_client(NewSpec)

    # 删除旧客户端
    p4.run('client', '-d', OldName)


def GetOpenedFiles(p4: P4, client_name: str) -> list:
    """获取指定客户端未提交的文件列表"""
    try:
        return p4.run("opened", "-C", client_name)
    except P4Exception as e:
        err_str = str(e).lower()
        if "not opened" in err_str or "no file(s)" in err_str:
            return []
        raise


def GetHaveList(p4: P4, command_target: str) -> set:
    """获取 have list 中的本地路径集合"""
    result = p4.run("have", command_target)
    paths = set()
    for item in result:
        if isinstance(item, dict) and item.get('path'):
            paths.add(os.path.normcase(os.path.normpath(item['path'])))
    return paths


def GetDifferentFiles(p4: P4, command_target: str) -> list:
    """获取内容不同的文件列表（depot 有，本地内容不同）"""
    try:
        result = p4.run("diff", "-se", command_target)
        return [item.get('depotFile', '') for item in result if isinstance(item, dict)]
    except P4Exception as e:
        err_str = str(e).lower()
        if "no file(s)" in err_str or "not on client" in err_str:
            return []
        raise


def GetMissingFiles(p4: P4, command_target: str) -> list:
    """获取缺失的文件列表（depot 有，本地没有）"""
    try:
        result = p4.run("diff", "-sd", command_target)
        return [item.get('depotFile', '') for item in result if isinstance(item, dict)]
    except P4Exception as e:
        err_str = str(e).lower()
        if "no file(s)" in err_str or "not on client" in err_str:
            return []
        raise


def SyncFiles(p4: P4, files: list, handler: OutputHandler = None, parallel: int = 4):
    """同步指定文件列表（使用 sync -f 强制同步）"""
    if not files:
        return
    if handler:
        p4.handler = handler
    args = ["sync", "-f"]
    if parallel > 0:
        args.append(f"--parallel=threads={parallel}")
    args.extend(files)
    p4.run(*args)


class P4IgnoreParser:
    """解析 .p4ignore 文件"""

    # 默认忽略规则（即使没有 .p4ignore 文件也会应用）
    DEFAULT_PATTERNS = [
        "Saved/",
        "Intermediate/",
        "DerivedDataCache/",
        "Binaries/",
        ".vs/",
        ".idea/",
        ".git/",
        "*.log",
    ]

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.patterns = list(self.DEFAULT_PATTERNS)
        self.negations = []
        self._Load()

    def _Load(self):
        """读取并解析 .p4ignore 文件"""
        p4ignore_path = os.path.join(self.workspace_root, ".p4ignore")
        if not os.path.exists(p4ignore_path):
            return
        with open(p4ignore_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('!'):
                    self.negations.append(line[1:])
                else:
                    self.patterns.append(line)

    def ShouldIgnore(self, file_path: str) -> bool:
        """判断文件是否应该被忽略"""
        rel_path = os.path.relpath(file_path, self.workspace_root).replace('\\', '/')
        for pattern in self.negations:
            if self._Match(rel_path, pattern):
                return False
        for pattern in self.patterns:
            if self._Match(rel_path, pattern):
                return True
        return False

    def _Match(self, path: str, pattern: str) -> bool:
        """匹配路径和模式"""
        if pattern.endswith('/'):
            dir_pattern = pattern.rstrip('/')
            # 检查路径中的所有部分（包括最后一个，以支持目录检查）
            for part in path.split('/'):
                if fnmatch.fnmatch(part, dir_pattern):
                    return True
            return False
        if '/' in pattern:
            return fnmatch.fnmatch(path, pattern)
        return fnmatch.fnmatch(os.path.basename(path), pattern)


def DeleteObsoleteFiles(workspace_root: str, have_paths: set, ignore_parser: P4IgnoreParser, log_callback=None) -> int:
    """删除多余的版本控制文件（本地有，have list 没有，且不在 .p4ignore 中）"""
    deleted_count = 0
    for root, dirs, files in os.walk(workspace_root):
        dirs[:] = [d for d in dirs if not ignore_parser.ShouldIgnore(os.path.join(root, d))]
        for file in files:
            file_path = os.path.join(root, file)
            normalized_path = os.path.normcase(os.path.normpath(file_path))
            if normalized_path in have_paths:
                continue
            if ignore_parser.ShouldIgnore(file_path):
                continue
            try:
                os.chmod(file_path, stat.S_IWRITE)
                os.remove(file_path)
                deleted_count += 1
                if log_callback:
                    log_callback(f"删除: {file_path}")
            except Exception as e:
                if log_callback:
                    log_callback(f"删除失败: {file_path} - {e}")
    return deleted_count


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


def RunSync(p4: P4, command_target: str, handler: OutputHandler = None, flush_only: bool = True, parallel: int = 0):
    """执行 sync 命令（flush_only=True 时只更新 have list，不下载文件）"""
    if handler:
        p4.handler = handler
    args = ["sync"]
    if flush_only:
        args.append("-k")
    if parallel > 0:
        args.append(f"--parallel=threads={parallel}")
    args.append(command_target)
    p4.run(*args)


def RunReconcile(p4: P4, command_target: str, parallel: int = 8) -> dict:
    """执行 reconcile 命令，返回统计结果"""
    result = {"edit": 0, "add": 0, "delete": 0}
    try:
        args = ["reconcile"]
        if parallel > 0:
            args.append(f"--parallel=threads={parallel}")
        args.append(command_target)
        output = p4.run(*args)
        for item in output:
            if isinstance(item, dict):
                action = item.get("action", "")
                if action in result:
                    result[action] += 1
    except P4Exception as e:
        err_str = str(e).lower()
        if "no file(s)" not in err_str:
            raise
    return result


def LaunchP4V(server: str = None, user: str = None, client: str = None):
    """启动 P4V 客户端，可指定服务器、用户和客户端"""
    try:
        args = ['p4v']
        if server:
            args.extend(['-p', server])
        if user:
            args.extend(['-u', user])
        if client:
            args.extend(['-c', client])

        if platform.system() == 'Windows':
            subprocess.Popen(args, shell=True)
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', '-a', 'p4v', '--args'] + args[1:])
        else:
            subprocess.Popen(args)
    except Exception:
        pass

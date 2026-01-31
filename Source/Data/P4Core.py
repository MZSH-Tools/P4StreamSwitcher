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
            Output = subprocess.check_output(['tasklist'], universal_newlines=True)
            return 'p4v.exe' in Output.lower()
        else:
            Output = subprocess.check_output(['pgrep', '-x', 'p4v'], stderr=subprocess.DEVNULL)
            return bool(Output.strip())
    except Exception:
        return False


def GetLocalStreamClients(P4Conn: P4):
    """获取本地主机上当前用户的所有流客户端"""
    LocalHostname = socket.gethostname()
    Clients = P4Conn.run_clients()
    LocalStreamClients = []
    for Client in Clients:
        ClientHost = Client.get('Host', '')
        ClientUser = Client.get('Owner', '')
        if ClientHost.lower() == LocalHostname.lower() and ClientUser == P4Conn.user and 'Stream' in Client:
            LocalStreamClients.append(Client.get('client', P4Conn.client))
    return LocalStreamClients


def GetAllStreams(P4Conn: P4):
    """获取所有流"""
    return P4Conn.run_streams()


def GetAllClients(P4Conn: P4):
    """获取所有客户端"""
    return P4Conn.run_clients()


def GetMainlineProjects(P4Conn: P4):
    """获取所有主线类型的流项目"""
    Streams = P4Conn.run_streams()
    Projects = []
    for S in Streams:
        if S.get('Type', '') == 'mainline':
            Parsed = ParseStreamPath(S.get('Stream', ''))
            Projects.append(Parsed[0])
    return Projects


def GetProjectStreams(P4Conn: P4, ProjectName: str):
    """获取指定项目下的所有流分支"""
    Streams = P4Conn.run_streams()
    Values = []
    for S in Streams:
        Parsed = ParseStreamPath(S.get('Stream', ''))
        if Parsed[0] == ProjectName:
            Values.append(Parsed[1])
    return Values


def ParseStreamPath(StreamPath: str):
    """解析流路径，返回 [项目名, 分支名]"""
    return StreamPath.split('/')[-2:]


def GetClientInfo(P4Conn: P4, ClientName: str):
    """获取客户端信息"""
    for Client in P4Conn.run_clients():
        if Client.get('client', '') == ClientName:
            return Client
    return None


def CheckTagConflict(P4Conn: P4, Tag: str) -> list:
    """检查标识是否被其他主机使用，返回冲突的客户端列表"""
    if not Tag:
        return []
    LocalHost = socket.gethostname().lower()
    Prefix = f"{Tag}_"
    Conflicts = []
    for Client in P4Conn.run_clients():
        Name = Client.get('client', '')
        Host = Client.get('Host', '').lower()
        # 匹配 标识_项目_分支 格式
        if Name.startswith(Prefix):
            Parts = Name[len(Prefix):].split('_')
            if len(Parts) >= 2 and Host != LocalHost:
                Conflicts.append(Name)
    return Conflicts


def GetLocalClientsWithTag(P4Conn: P4, Tag: str) -> list:
    """获取本地使用指定标识的客户端列表"""
    if not Tag:
        return []
    LocalHost = socket.gethostname().lower()
    Prefix = f"{Tag}_"
    Clients = []
    for Client in P4Conn.run_clients():
        Name = Client.get('client', '')
        Host = Client.get('Host', '').lower()
        Owner = Client.get('Owner', '')
        # 匹配 标识_项目_分支 格式，本地且属于当前用户
        if Name.startswith(Prefix) and Host == LocalHost and Owner == P4Conn.user:
            Parts = Name[len(Prefix):].split('_')
            if len(Parts) >= 2:
                Clients.append(Name)
    return Clients


def GetLocalClientsWithTagInfo(P4Conn: P4, Tag: str) -> list:
    """获取本地使用指定标识的客户端详细信息列表（含 Access 时间）"""
    if not Tag:
        return []
    LocalHost = socket.gethostname().lower()
    Prefix = f"{Tag}_"
    Clients = []
    for Client in P4Conn.run_clients():
        Name = Client.get('client', '')
        Host = Client.get('Host', '').lower()
        Owner = Client.get('Owner', '')
        # 匹配 标识_项目_分支 格式，本地且属于当前用户
        if Name.startswith(Prefix) and Host == LocalHost and Owner == P4Conn.user:
            Parts = Name[len(Prefix):].split('_')
            if len(Parts) >= 2:
                Clients.append(Client)
    return Clients


def GetOldestLocalClient(P4Conn: P4, Tag: str) -> str | None:
    """获取本地最旧的工作区名称（基于 Access 时间）"""
    Clients = GetLocalClientsWithTagInfo(P4Conn, Tag)
    if not Clients:
        return None
    # 按 Access 时间排序，返回最旧的
    Clients.sort(key=lambda C: int(C.get('Access', '0')))
    return Clients[0].get('client')


def CreateP4ConfigFile(WorkspaceRoot: str, ClientName: str, Server: str, User: str):
    """在工作区根目录创建 .p4config 文件"""
    ConfigPath = os.path.join(WorkspaceRoot, ".p4config")
    with open(ConfigPath, 'w', encoding='utf-8') as F:
        F.write(f"P4CLIENT={ClientName}\n")
        F.write(f"P4PORT={Server}\n")
        F.write(f"P4USER={User}\n")


def CreateStreamClient(P4Conn: P4, ClientName: str, StreamPath: str, WorkspaceRoot: str, AutoRmdir: bool = False):
    """创建新的流客户端"""
    P4Conn.client = ClientName
    Spec = P4Conn.fetch_client()
    Spec['Host'] = socket.gethostname()
    Spec['Stream'] = StreamPath
    Spec['Root'] = WorkspaceRoot

    # 处理 rmdir 选项
    if AutoRmdir:
        Options = Spec.get('Options', '')
        # 移除 normdir，确保 rmdir 存在
        Options = Options.replace('normdir', '').strip()
        Options = ' '.join(Options.split())  # 清理多余空格
        if 'rmdir' not in Options:
            Options = Options + ' rmdir' if Options else 'rmdir'
        Spec['Options'] = Options

    P4Conn.save_client(Spec)


def ClientExists(P4Conn: P4, ClientName: str) -> bool:
    """检查客户端是否存在"""
    for Client in P4Conn.run_clients():
        if Client.get('client') == ClientName:
            return True
    return False


def UpdateClientRmdir(P4Conn: P4, ClientName: str, AutoRmdir: bool):
    """更新客户端的 rmdir 选项"""
    OldClient = P4Conn.client
    try:
        P4Conn.client = ClientName
        Spec = P4Conn.fetch_client()
        Options = Spec.get('Options', '')

        if AutoRmdir:
            # 移除 normdir，确保 rmdir 存在
            Options = Options.replace('normdir', '').strip()
            Options = ' '.join(Options.split())
            if 'rmdir' not in Options:
                Options = Options + ' rmdir' if Options else 'rmdir'
        else:
            # 移除 rmdir，确保 normdir 存在
            Options = Options.replace('rmdir', '').strip()
            Options = ' '.join(Options.split())
            if 'normdir' not in Options:
                Options = Options + ' normdir' if Options else 'normdir'

        Spec['Options'] = Options
        P4Conn.save_client(Spec)
    finally:
        P4Conn.client = OldClient


def DeleteClient(P4Conn: P4, ClientName: str):
    """删除客户端"""
    P4Conn.run('client', '-d', ClientName)


def RenameClient(P4Conn: P4, OldName: str, NewName: str):
    """重命名客户端"""
    # 获取旧客户端配置
    P4Conn.client = OldName
    OldSpec = P4Conn.fetch_client()

    # 创建新客户端
    P4Conn.client = NewName
    NewSpec = P4Conn.fetch_client()
    for Key in ['Root', 'Stream', 'Options', 'SubmitOptions', 'LineEnd']:
        if Key in OldSpec:
            NewSpec[Key] = OldSpec[Key]
    P4Conn.save_client(NewSpec)

    # 删除旧客户端
    P4Conn.run('client', '-d', OldName)


def GetOpenedFiles(P4Conn: P4, ClientName: str) -> list:
    """获取指定客户端未提交的文件列表"""
    try:
        return P4Conn.run("opened", "-C", ClientName)
    except P4Exception as E:
        ErrStr = str(E).lower()
        if "not opened" in ErrStr or "no file(s)" in ErrStr:
            return []
        raise


def GetHaveList(P4Conn: P4, CmdTarget: str) -> set:
    """获取 have list 中的本地路径集合"""
    Result = P4Conn.run("have", CmdTarget)
    Paths = set()
    for Item in Result:
        if isinstance(Item, dict) and Item.get('path'):
            Paths.add(os.path.normcase(os.path.normpath(Item['path'])))
    return Paths


def GetDifferentFiles(P4Conn: P4, CmdTarget: str) -> list:
    """获取内容不同的文件列表（depot 有，本地内容不同）"""
    try:
        Result = P4Conn.run("diff", "-se", CmdTarget)
        return [Item.get('depotFile', '') for Item in Result if isinstance(Item, dict)]
    except P4Exception as E:
        ErrStr = str(E).lower()
        if "no file(s)" in ErrStr or "not on client" in ErrStr:
            return []
        raise


def GetMissingFiles(P4Conn: P4, CmdTarget: str) -> list:
    """获取缺失的文件列表（depot 有，本地没有）"""
    try:
        Result = P4Conn.run("diff", "-sd", CmdTarget)
        return [Item.get('depotFile', '') for Item in Result if isinstance(Item, dict)]
    except P4Exception as E:
        ErrStr = str(E).lower()
        if "no file(s)" in ErrStr or "not on client" in ErrStr:
            return []
        raise


def SyncFiles(P4Conn: P4, Files: list, Handler: OutputHandler = None, Parallel: int = 4):
    """同步指定文件列表（使用 sync -f 强制同步）"""
    if not Files:
        return
    if Handler:
        P4Conn.handler = Handler
    Args = ["sync", "-f"]
    if Parallel > 0:
        Args.append(f"--parallel=threads={Parallel}")
    Args.extend(Files)
    P4Conn.run(*Args)


class P4IgnoreParser:
    """解析 .p4ignore 文件"""

    # 默认忽略规则（即使没有 .p4ignore 文件也会应用）
    DEFAULT_PATTERNS = [
        "Saved/",
        "Intermediate/",
        "DerivedDataCache/",
        "Binaries/",
        ".vs/",
        ".vscode/",
        ".idea/",
        ".git/",
        ".p4config",
        "*.log",
    ]

    def __init__(self, WorkspaceRoot: str):
        self.workspace_root = WorkspaceRoot
        self.patterns = list(self.DEFAULT_PATTERNS)
        self.negations = []
        self._Load()

    def _Load(self):
        """读取并解析 .p4ignore 文件"""
        P4IgnorePath = os.path.join(self.workspace_root, ".p4ignore")
        if not os.path.exists(P4IgnorePath):
            return
        with open(P4IgnorePath, 'r', encoding='utf-8', errors='ignore') as F:
            for Line in F:
                Line = Line.strip()
                if not Line or Line.startswith('#'):
                    continue
                if Line.startswith('!'):
                    self.negations.append(Line[1:])
                else:
                    self.patterns.append(Line)

    def ShouldIgnore(self, FilePath: str) -> bool:
        """判断文件是否应该被忽略"""
        RelPath = os.path.relpath(FilePath, self.workspace_root).replace('\\', '/')
        for Pattern in self.negations:
            if self._Match(RelPath, Pattern):
                return False
        for Pattern in self.patterns:
            if self._Match(RelPath, Pattern):
                return True
        return False

    def _Match(self, Path: str, Pattern: str) -> bool:
        """匹配路径和模式"""
        if Pattern.endswith('/'):
            DirPattern = Pattern.rstrip('/')
            # 检查路径中的所有部分（包括最后一个，以支持目录检查）
            for Part in Path.split('/'):
                if fnmatch.fnmatch(Part, DirPattern):
                    return True
            return False
        if '/' in Pattern:
            return fnmatch.fnmatch(Path, Pattern)
        return fnmatch.fnmatch(os.path.basename(Path), Pattern)


def DeleteObsoleteFiles(WorkspaceRoot: str, HavePaths: set, IgnoreParser: P4IgnoreParser, LogCallback=None) -> int:
    """删除多余的版本控制文件（本地有，have list 没有，且不在 .p4ignore 中）"""
    DeletedCnt = 0
    for Root, Dirs, Files in os.walk(WorkspaceRoot):
        Dirs[:] = [D for D in Dirs if not IgnoreParser.ShouldIgnore(os.path.join(Root, D))]
        for File in Files:
            FilePath = os.path.join(Root, File)
            NormalizedPath = os.path.normcase(os.path.normpath(FilePath))
            if NormalizedPath in HavePaths:
                continue
            if IgnoreParser.ShouldIgnore(FilePath):
                continue
            try:
                os.chmod(FilePath, stat.S_IWRITE)
                os.remove(FilePath)
                DeletedCnt += 1
                if LogCallback:
                    LogCallback(f"删除: {FilePath}")
            except Exception as E:
                if LogCallback:
                    LogCallback(f"删除失败: {FilePath} - {E}")
    return DeletedCnt


class PreviewOutputHandler(OutputHandler):
    """用于统计文件数量的 Handler"""
    def __init__(self):
        super().__init__()
        self.count = 0

    def outputStat(self, Stat):
        self.count += 1
        return OutputHandler.HANDLED


class SyncOutputHandler(OutputHandler):
    """用于同步操作的 Handler，支持进度回调"""
    def __init__(self, OnFileProcessed=None, OnText=None):
        super().__init__()
        self.processed_files = 0
        self.on_file_processed = OnFileProcessed
        self.on_text = OnText

    def outputStat(self, Stat):
        self.processed_files += 1
        if self.on_file_processed:
            self.on_file_processed(self.processed_files, Stat.get('depotFile', ''))
        return OutputHandler.HANDLED

    def outputText(self, Text):
        if self.on_text:
            self.on_text(Text)
        return OutputHandler.HANDLED

    def outputInfo(self, Info):
        if self.on_text:
            self.on_text(Info)
        return OutputHandler.HANDLED


def RunSync(P4Conn: P4, CmdTarget: str, Handler: OutputHandler = None, FlushOnly: bool = True, Parallel: int = 0):
    """执行 sync 命令（FlushOnly=True 时只更新 have list，不下载文件）"""
    if Handler:
        P4Conn.handler = Handler
    Args = ["sync"]
    if FlushOnly:
        Args.append("-k")
    if Parallel > 0:
        Args.append(f"--parallel=threads={Parallel}")
    Args.append(CmdTarget)
    P4Conn.run(*Args)


def RunReconcile(P4Conn: P4, CmdTarget: str, Parallel: int = 8) -> dict:
    """执行 reconcile 命令，返回统计结果"""
    Result = {"edit": 0, "add": 0, "delete": 0}
    try:
        Args = ["reconcile"]
        if Parallel > 0:
            Args.append(f"--parallel=threads={Parallel}")
        Args.append(CmdTarget)
        Output = P4Conn.run(*Args)
        for Item in Output:
            if isinstance(Item, dict):
                Action = Item.get("action", "")
                if Action in Result:
                    Result[Action] += 1
    except P4Exception as E:
        ErrStr = str(E).lower()
        if "no file(s)" not in ErrStr:
            raise
    return Result


def LaunchP4V(Server: str = None, User: str = None, Client: str = None):
    """启动 P4V 客户端，可指定服务器、用户和客户端"""
    try:
        Args = ['p4v']
        if Server:
            Args.extend(['-p', Server])
        if User:
            Args.extend(['-u', User])
        if Client:
            Args.extend(['-c', Client])

        if platform.system() == 'Windows':
            subprocess.Popen(Args, shell=True)
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', '-a', 'p4v', '--args'] + Args[1:])
        else:
            subprocess.Popen(Args)
    except Exception:
        pass

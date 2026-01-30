import os
import json
import time
from platformdirs import user_cache_dir


def GetCacheDir() -> str:
    """获取缓存目录路径"""
    return user_cache_dir("P4StreamSwitcher", "mengzhishanghun")


class GlobalConfig:
    """全局配置管理（工作区标识、最大工作区数量等）"""

    def __init__(self):
        self.cache_dir = GetCacheDir()
        self.config_file = os.path.join(self.cache_dir, "global_config.json")
        self.config = {
            "workspace_tag": "",
            "max_workspace_cnt": 5,
            "create_p4config": True,
            "auto_rmdir": True
        }
        self._Load()

    def _Load(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as F:
                    Loaded = json.load(F)
                    self.config.update(Loaded)
            except Exception:
                pass

    def _Save(self):
        """保存配置"""
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def GetWorkspaceTag(self) -> str:
        """获取工作区标识"""
        return self.config.get("workspace_tag", "")

    def SetWorkspaceTag(self, Tag: str):
        """设置工作区标识"""
        self.config["workspace_tag"] = Tag
        self._Save()

    def GetMaxWorkspaceCnt(self) -> int:
        """获取最大工作区数量"""
        return max(1, self.config.get("max_workspace_cnt", 5))

    def SetMaxWorkspaceCnt(self, Cnt: int):
        """设置最大工作区数量（最小为1）"""
        self.config["max_workspace_cnt"] = max(1, Cnt)
        self._Save()

    def GetCreateP4Config(self) -> bool:
        """获取是否创建 p4config 文件"""
        return self.config.get("create_p4config", True)

    def SetCreateP4Config(self, Enabled: bool):
        """设置是否创建 p4config 文件"""
        self.config["create_p4config"] = Enabled
        self._Save()

    def GetAutoRmdir(self) -> bool:
        """获取是否自动删除空文件夹"""
        return self.config.get("auto_rmdir", True)

    def SetAutoRmdir(self, Enabled: bool):
        """设置是否自动删除空文件夹"""
        self.config["auto_rmdir"] = Enabled
        self._Save()

    def GetWorkspaceTimestamps(self) -> dict:
        """获取工作区时间戳字典"""
        return self.config.get("workspace_timestamps", {})

    def UpdateWorkspaceTimestamp(self, ClientName: str):
        """更新工作区时间戳为当前时间"""
        Timestamps = self.config.get("workspace_timestamps", {})
        Timestamps[ClientName] = int(time.time())
        self.config["workspace_timestamps"] = Timestamps
        self._Save()

    def RemoveWorkspaceTimestamp(self, ClientName: str):
        """删除工作区时间戳"""
        Timestamps = self.config.get("workspace_timestamps", {})
        if ClientName in Timestamps:
            del Timestamps[ClientName]
            self.config["workspace_timestamps"] = Timestamps
            self._Save()

    def RenameWorkspaceTimestamp(self, OldName: str, NewName: str):
        """重命名工作区时间戳（迁移旧名称的时间戳到新名称）"""
        Timestamps = self.config.get("workspace_timestamps", {})
        if OldName in Timestamps:
            Timestamps[NewName] = Timestamps.pop(OldName)
            self.config["workspace_timestamps"] = Timestamps
            self._Save()

    def GetOldestWorkspace(self, ClientNames: list) -> str | None:
        """从给定列表中获取最旧的工作区名称"""
        if not ClientNames:
            return None
        Timestamps = self.config.get("workspace_timestamps", {})
        # 按时间戳排序，没有时间戳的视为最旧（0）
        Sorted = sorted(ClientNames, key=lambda N: Timestamps.get(N, 0))
        return Sorted[0]


class WorkspaceCache:
    """工作区目录缓存管理"""

    def __init__(self, client_name: str):
        self.client_name = client_name
        self.cache_dir = GetCacheDir()
        self.cache_file = os.path.join(self.cache_dir, f"{client_name}.json")
        self.cache = {}
        self._Load()

    def _Load(self):
        """加载缓存并转换旧格式"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                self._MigrateOldFormat()
            except Exception:
                self.cache = {}

    def _MigrateOldFormat(self):
        """将旧格式（字符串）转换为新格式（对象）"""
        Migrated = False
        for Key, Value in self.cache.items():
            if isinstance(Value, str):
                self.cache[Key] = {"workspace": Value, "offline": False}
                Migrated = True
        if Migrated:
            self._Save()

    def _Save(self):
        """保存缓存"""
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _GetEntry(self, StreamPath: str) -> dict | None:
        """获取缓存条目"""
        Entry = self.cache.get(StreamPath)
        if isinstance(Entry, str):
            return {"workspace": Entry, "offline": False}
        return Entry

    def Get(self, StreamPath: str) -> str | None:
        """获取缓存的工作区目录"""
        Entry = self._GetEntry(StreamPath)
        return Entry.get("workspace") if Entry else None

    def GetOffline(self, StreamPath: str) -> bool:
        """获取离线标记"""
        Entry = self._GetEntry(StreamPath)
        return Entry.get("offline", False) if Entry else False

    def Set(self, StreamPath: str, Workspace: str, Offline: bool = None):
        """设置工作区目录缓存，Offline 为 None 时保留原值"""
        Entry = self._GetEntry(StreamPath) or {"workspace": "", "offline": False}
        Entry["workspace"] = Workspace
        if Offline is not None:
            Entry["offline"] = Offline
        self.cache[StreamPath] = Entry
        self._Save()

    def SetOffline(self, StreamPath: str, Offline: bool):
        """设置离线标记"""
        Entry = self._GetEntry(StreamPath)
        if Entry:
            Entry["offline"] = Offline
            self.cache[StreamPath] = Entry
            self._Save()

    def SetNeedSync(self, StreamPath: str, NeedSync: bool):
        """设置流是否需要同步"""
        Entry = self._GetEntry(StreamPath)
        if Entry:
            Entry["need_sync"] = NeedSync
            self.cache[StreamPath] = Entry
            self._Save()

    def GetNeedSync(self, StreamPath: str) -> bool:
        """获取流是否需要同步，默认 False"""
        Entry = self._GetEntry(StreamPath)
        return Entry.get("need_sync", False) if Entry else False

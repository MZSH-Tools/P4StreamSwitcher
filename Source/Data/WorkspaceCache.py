import os
import json
import time
from platformdirs import user_cache_dir


def GetCacheDir() -> str:
    """获取缓存目录路径"""
    return user_cache_dir("P4StreamSwitcher", "mengzhishanghun")


class GlobalConfig:
    """全局配置管理（工作区标识、最大工作区数量、流缓存等）"""

    def __init__(self):
        self.CacheDir = GetCacheDir()
        self.ConfigFile = os.path.join(self.CacheDir, "config.json")
        self.Config = {
            "workspace_tag": "",
            "max_workspace_cnt": 5,
            "create_p4config": True,
            "auto_rmdir": True,
            "workspace_timestamps": {},
            "stream_cache": {}
        }
        self.Load()

    def Load(self):
        """加载配置"""
        if os.path.exists(self.ConfigFile):
            try:
                with open(self.ConfigFile, 'r', encoding='utf-8') as F:
                    Loaded = json.load(F)
                    self.Config.update(Loaded)
            except Exception:
                pass

    def Save(self):
        """保存配置"""
        os.makedirs(self.CacheDir, exist_ok=True)
        with open(self.ConfigFile, 'w', encoding='utf-8') as F:
            json.dump(self.Config, F, ensure_ascii=False, indent=2)

    def GetWorkspaceTag(self) -> str:
        """获取工作区标识"""
        return self.Config.get("workspace_tag", "")

    def SetWorkspaceTag(self, Tag: str):
        """设置工作区标识"""
        self.Config["workspace_tag"] = Tag
        self.Save()

    def GetMaxWorkspaceCnt(self) -> int:
        """获取最大工作区数量"""
        return max(1, self.Config.get("max_workspace_cnt", 5))

    def SetMaxWorkspaceCnt(self, Cnt: int):
        """设置最大工作区数量（最小为1）"""
        self.Config["max_workspace_cnt"] = max(1, Cnt)
        self.Save()

    def GetCreateP4Config(self) -> bool:
        """获取是否创建 p4config 文件"""
        return self.Config.get("create_p4config", True)

    def SetCreateP4Config(self, Enabled: bool):
        """设置是否创建 p4config 文件"""
        self.Config["create_p4config"] = Enabled
        self.Save()

    def GetAutoRmdir(self) -> bool:
        """获取是否自动删除空文件夹"""
        return self.Config.get("auto_rmdir", True)

    def SetAutoRmdir(self, Enabled: bool):
        """设置是否自动删除空文件夹"""
        self.Config["auto_rmdir"] = Enabled
        self.Save()

    def GetWorkspaceTimestamps(self) -> dict:
        """获取工作区时间戳字典"""
        return self.Config.get("workspace_timestamps", {})

    def UpdateWorkspaceTimestamp(self, ClientName: str):
        """更新工作区时间戳为当前时间"""
        Timestamps = self.Config.get("workspace_timestamps", {})
        Timestamps[ClientName] = int(time.time())
        self.Config["workspace_timestamps"] = Timestamps
        self.Save()

    def RemoveWorkspaceTimestamp(self, ClientName: str):
        """删除工作区时间戳"""
        Timestamps = self.Config.get("workspace_timestamps", {})
        if ClientName in Timestamps:
            del Timestamps[ClientName]
            self.Config["workspace_timestamps"] = Timestamps
            self.Save()

    def RenameWorkspaceTimestamp(self, OldName: str, NewName: str):
        """重命名工作区时间戳（迁移旧名称的时间戳到新名称）"""
        Timestamps = self.Config.get("workspace_timestamps", {})
        if OldName in Timestamps:
            Timestamps[NewName] = Timestamps.pop(OldName)
            self.Config["workspace_timestamps"] = Timestamps
            self.Save()

    def GetOldestWorkspace(self, ClientNames: list) -> str | None:
        """从给定列表中获取最旧的工作区名称"""
        if not ClientNames:
            return None
        Timestamps = self.Config.get("workspace_timestamps", {})
        # 按时间戳排序，没有时间戳的视为最旧（0）
        Sorted = sorted(ClientNames, key=lambda N: Timestamps.get(N, 0))
        return Sorted[0]

    # ========== 流缓存相关方法 ==========

    def GetStreamEntry(self, StreamPath: str) -> dict | None:
        """获取流缓存条目"""
        Cache = self.Config.get("stream_cache", {})
        return Cache.get(StreamPath)

    def GetStreamWorkspace(self, StreamPath: str) -> str | None:
        """获取缓存的工作区目录"""
        Entry = self.GetStreamEntry(StreamPath)
        return Entry.get("workspace") if Entry else None

    def GetStreamOffline(self, StreamPath: str) -> bool:
        """获取离线标记"""
        Entry = self.GetStreamEntry(StreamPath)
        return Entry.get("offline", False) if Entry else False

    def SetStreamCache(self, StreamPath: str, Workspace: str, Offline: bool = None):
        """设置工作区目录缓存，Offline 为 None 时保留原值"""
        Cache = self.Config.get("stream_cache", {})
        Entry = Cache.get(StreamPath) or {"workspace": "", "offline": False}
        Entry["workspace"] = Workspace
        if Offline is not None:
            Entry["offline"] = Offline
        Cache[StreamPath] = Entry
        self.Config["stream_cache"] = Cache
        self.Save()

    def SetStreamOffline(self, StreamPath: str, Offline: bool):
        """设置离线标记"""
        Cache = self.Config.get("stream_cache", {})
        Entry = Cache.get(StreamPath)
        if Entry:
            Entry["offline"] = Offline
            Cache[StreamPath] = Entry
            self.Config["stream_cache"] = Cache
            self.Save()

    def SetStreamNeedSync(self, StreamPath: str, NeedSync: bool):
        """设置流是否需要同步"""
        Cache = self.Config.get("stream_cache", {})
        Entry = Cache.get(StreamPath)
        if Entry:
            Entry["need_sync"] = NeedSync
            Cache[StreamPath] = Entry
            self.Config["stream_cache"] = Cache
            self.Save()

    def GetStreamNeedSync(self, StreamPath: str) -> bool:
        """获取流是否需要同步，默认 False"""
        Entry = self.GetStreamEntry(StreamPath)
        return Entry.get("need_sync", False) if Entry else False

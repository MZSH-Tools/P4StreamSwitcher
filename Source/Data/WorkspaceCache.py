import os
import json
from platformdirs import user_cache_dir


def GetCacheDir() -> str:
    """获取缓存目录路径"""
    return user_cache_dir("P4StreamSwitcher", "mengzhishanghun")


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
        migrated = False
        for key, value in self.cache.items():
            if isinstance(value, str):
                self.cache[key] = {"workspace": value, "offline": False}
                migrated = True
        if migrated:
            self._Save()

    def _Save(self):
        """保存缓存"""
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _GetEntry(self, stream_path: str) -> dict | None:
        """获取缓存条目"""
        entry = self.cache.get(stream_path)
        if isinstance(entry, str):
            return {"workspace": entry, "offline": False}
        return entry

    def Get(self, stream_path: str) -> str | None:
        """获取缓存的工作区目录"""
        entry = self._GetEntry(stream_path)
        return entry.get("workspace") if entry else None

    def GetOffline(self, stream_path: str) -> bool:
        """获取离线标记"""
        entry = self._GetEntry(stream_path)
        return entry.get("offline", False) if entry else False

    def Set(self, stream_path: str, workspace: str, offline: bool = None):
        """设置工作区目录缓存，offline 为 None 时保留原值"""
        entry = self._GetEntry(stream_path) or {"workspace": "", "offline": False}
        entry["workspace"] = workspace
        if offline is not None:
            entry["offline"] = offline
        self.cache[stream_path] = entry
        self._Save()

    def SetOffline(self, stream_path: str, offline: bool):
        """设置离线标记"""
        entry = self._GetEntry(stream_path)
        if entry:
            entry["offline"] = offline
            self.cache[stream_path] = entry
            self._Save()

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
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _Save(self):
        """保存缓存"""
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def Get(self, stream_path: str) -> str | None:
        """获取缓存的工作区目录"""
        return self.cache.get(stream_path)

    def Set(self, stream_path: str, workspace: str):
        """设置工作区目录缓存"""
        self.cache[stream_path] = workspace
        self._Save()

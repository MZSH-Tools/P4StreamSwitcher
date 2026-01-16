import os
import json
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
            "left_panel_visible": True,
            "right_panel_visible": True
        }
        self._Load()

    def _Load(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
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

    def SetWorkspaceTag(self, tag: str):
        """设置工作区标识"""
        self.config["workspace_tag"] = tag
        self._Save()

    def GetMaxWorkspaceCnt(self) -> int:
        """获取最大工作区数量"""
        return max(1, self.config.get("max_workspace_cnt", 5))

    def SetMaxWorkspaceCnt(self, cnt: int):
        """设置最大工作区数量（最小为1）"""
        self.config["max_workspace_cnt"] = max(1, cnt)
        self._Save()

    def GetLeftPanelVisible(self) -> bool:
        """获取左侧面板可见状态"""
        return self.config.get("left_panel_visible", True)

    def SetLeftPanelVisible(self, visible: bool):
        """设置左侧面板可见状态"""
        self.config["left_panel_visible"] = visible
        self._Save()

    def GetRightPanelVisible(self) -> bool:
        """获取右侧面板可见状态"""
        return self.config.get("right_panel_visible", True)

    def SetRightPanelVisible(self, visible: bool):
        """设置右侧面板可见状态"""
        self.config["right_panel_visible"] = visible
        self._Save()


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

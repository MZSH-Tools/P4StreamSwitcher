import sys
import os
import shutil
import tempfile
import tkinter as tk
from tkinter import messagebox
from P4 import P4, P4Exception

# PyInstaller 打包后隐藏控制台窗口（解决 console=False 的 bootloader bug）
if getattr(sys, 'frozen', False):
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

from Source.UI.UIComponents import AppUI
from Source.Logic.Callbacks import AppCallbacks
from Source.Data.P4Core import GetLocalStreamClients


def CleanupMeiDirs():
    """清理 PyInstaller 遗留的 _MEI 临时目录"""
    if not getattr(sys, 'frozen', False):
        return  # 非打包环境，不处理

    CurMeiDir = getattr(sys, '_MEIPASS', None)
    TempDir = tempfile.gettempdir()

    for Name in os.listdir(TempDir):
        if Name.startswith('_MEI'):
            Path = os.path.join(TempDir, Name)
            # 跳过当前正在使用的目录
            if CurMeiDir and os.path.normcase(Path) == os.path.normcase(CurMeiDir):
                continue
            try:
                shutil.rmtree(Path)
            except Exception:
                pass  # 忽略删除失败（可能被其他进程占用）


def main():
    CleanupMeiDirs()  # 清理旧的临时目录

    Root = tk.Tk()
    UI = AppUI(Root)

    try:
        P4Conn = P4()
        try:
            P4Conn.connect()
        except P4Exception:
            messagebox.showerror("连接服务器失败", "请检查p4 set中P4PORT")
            sys.exit()

        UI.LogMessage("成功连接到 P4 服务器！")

        # 获取本地流客户端
        LocalStreamClients = GetLocalStreamClients(P4Conn)
        if P4Conn.client not in LocalStreamClients:
            if len(LocalStreamClients) > 0:
                P4Conn.client = LocalStreamClients[0]
            else:
                messagebox.showerror("未检测到流客户端", f"未在本地检测到用户{P4Conn.user}所属的流客户端")
                sys.exit()

        # 初始化回调
        Callbacks = AppCallbacks(P4Conn, UI)
        Callbacks.Initialize(P4Conn.client)

        # 启动主循环
        Root.mainloop()

    except P4Exception as E:
        if 'User' in str(E) and "doesn't exist" in str(E):
            messagebox.showerror("用户设置错误", "请检查p4 set中P4USER")
        ErrMsgs = P4Conn.errors if P4Conn.errors else [str(E)]
        messagebox.showerror("程序运行错误", "\n".join(ErrMsgs))
        UI.LogError("\n".join(ErrMsgs))
    finally:
        if P4Conn.connected():
            P4Conn.disconnect()
            UI.LogMessage("P4服务器已断开，请确保服务器正确开启后重启该软件")


if __name__ == "__main__":
    main()

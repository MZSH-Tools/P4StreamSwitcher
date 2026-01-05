import sys
import tkinter as tk
from tkinter import messagebox
from P4 import P4, P4Exception

from Source.UI.UIComponents import AppUI
from Source.Logic.Callbacks import AppCallbacks
from Source.Data.P4Core import GetLocalStreamClients


def main():
    root = tk.Tk()
    ui = AppUI(root)

    try:
        p4 = P4()
        try:
            p4.connect()
        except P4Exception:
            messagebox.showerror("连接服务器失败", "请检查p4 set中P4PORT")
            sys.exit()

        ui.LogMessage("成功连接到 P4 服务器！")
        ui.p4_server_var.set(p4.port)
        ui.p4_user_var.set(p4.user)

        # 获取本地流客户端
        local_stream_clients = GetLocalStreamClients(p4)
        if p4.client not in local_stream_clients:
            if len(local_stream_clients) > 0:
                p4.client = local_stream_clients[0]
            else:
                messagebox.showerror("未检测到流客户端", f"未在本地检测到用户{p4.user}所属的流客户端")
                sys.exit()

        ui.p4_client_var.set(p4.client)

        # 初始化回调
        callbacks = AppCallbacks(p4, ui)
        callbacks.Initialize()

        # 启动主循环
        root.mainloop()

    except P4Exception as e:
        if 'User' in str(e) and "doesn't exist" in str(e):
            messagebox.showerror("用户设置错误", "请检查p4 set中P4USER")
        messagebox.showerror("程序运行错误", "\n".join(p4.errors))
        ui.LogMessage("\n".join(p4.errors))
    finally:
        if p4.connected():
            p4.disconnect()
            ui.LogMessage("P4服务器已断开，请确保服务器正确开启后重启该软件")


if __name__ == "__main__":
    main()

from P4 import P4, P4Exception, OutputHandler
import socket
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sys
import os
import threading

# 日志信息输出
def log_message(message):
    """在日志输出区添加一条消息"""
    def append_message():
        log_text.configure(state='normal')
        log_text.insert('end', message + '\n')
        log_text.configure(state='disabled')
        log_text.see('end')  # 滚动到最后一行
    root.after(0, append_message)

# 清空日志
def clear_log():
    def clear():
        log_text.configure(state='normal')
        log_text.delete('1.0', tk.END)
        log_text.configure(state='disabled')
    root.after(0, clear)

# 更新进度条
def update_progress(current, total):
    percentage = int((current / total) * 100)
    def update():
        progress_bar['value'] = percentage
        progress_percentage_label.configure(text=f"{percentage}%")
    root.after(0, update)

# 更新当前操作标签
def update_operation_label(text):
    def update():
        operation_label.configure(text=text)
    root.after(0, update)

def get_local_stream_clients():
    # 获取本地主机名
    local_hostname = socket.gethostname()

    # 获取所有客户端（工作区）
    clients = p4.run_clients()
    local_stream_clients = []
    for client in clients:
        client_host = client.get('Host', '')
        client_user = client.get('Owner', '')

        # 检查 Host 是否与当前主机匹配，并且存在 'Stream' 字段
        if client_host.lower() == local_hostname.lower() and client_user == p4.user and 'Stream' in client:
            local_stream_clients.append(client.get('client', p4.client))
    return local_stream_clients

# 更新客户端下拉列表
def update_client_combobox(event=None):
    client_combo['values'] = get_local_stream_clients()

def select_client_combobox(event=None):
    global select_stream_path
    cur_client = p4_client_var.get()
    for client in p4.run_clients():
        if client.get('client', '') == cur_client:
            select_stream_path = client.get('Stream', '')
            parse_stream = parse_stream_path(select_stream_path)
            p4_project_var.set(parse_stream[0])
            p4_stream_var.set(parse_stream[1])
    # 数据重置
    reset_default_var()

# 更新项目下拉列表
def update_project_combobox(event=None):
    # 获取所有流
    streams = p4.run_streams()
    projects = []
    for stream in streams:
        stream_Type = stream.get('Type', '')
        # 仅添加主线类型的流
        if stream_Type == 'mainline':
            parse_stream = parse_stream_path(stream.get('Stream',''))
            projects.append(parse_stream[0])
    project_combo['values'] = projects

def select_project_combobox(event=None):
    global select_stream_path
    select_project = p4_project_var.get()
    if select_project == default_project_var:
        p4_stream_var.set(default_stream_var)
        select_stream_path = default_stream_path_var
    else:
        # 获取所有流
        streams = p4.run_streams()
        for stream in streams:
            if stream.get('Type') == 'mainline':
                parse_stream = parse_stream_path(stream.get('Stream', ''))
                if parse_stream[0] == select_project:
                    p4_stream_var.set(parse_stream[1])
                    select_stream_path = stream.get('Stream', '')
                    break
    update_workspace_text()

# 更新流下拉列表
def update_stream_combobox(event=None):
    # 获取所有流
    streams = p4.run_streams()
    cur_project = p4_project_var.get()
    values = []
    for stream in streams:
        parse_stream = parse_stream_path(stream.get('Stream', ''))
        if parse_stream[0] == cur_project:
            values.append(parse_stream[1])
    stream_combo['values'] = values

def select_stream_combobox(event=None):
    global select_stream_path
    path_array = select_stream_path.split('/')[-3:-1]
    select_stream_path = f"//{path_array[0]}/{path_array[1]}/{p4_stream_var.get()}"

# 更新工作区目录
def update_workspace_text():
    global default_workspace_root_var
    p4_workspace_var.set(os.path.join(default_workspace_root_var, p4_project_var.get()))

def reset_default_var():
    global default_project_var, default_stream_var, default_workspace_root_var ,default_stream_path_var
    default_project_var = p4_project_var.get()
    default_stream_var = p4_stream_var.get()
    cur_client = p4_client_var.get()
    for client in p4.run_clients():
        if client.get('client', '') == cur_client:
            default_stream_path_var = client.get('Stream', '')
            default_workspace_root_var = client.get('Root','')
            workspace_array = default_workspace_root_var.split('\\')[:-1]
            workspace_array.insert(1,'\\')
            default_workspace_root_var = os.path.join(*workspace_array)
            break
    update_workspace_text()

def parse_stream_path(stream_path):
    return stream_path.split('/')[-2:]

def run_sync_and_clean():
    try:
        update_operation_label("正在连接服务器...")
        command_target = f"//{p4_client_var.get()}/..."
        # 创建新的 P4 实例
        p4_thread = P4()
        p4_thread.connect()

        # 使用自定义的Handler来统计总的文件数
        class PreviewOutputHandler(OutputHandler):
            def __init__(self):
                super().__init__()
                self.count = 0

            def outputStat(self, stat):
                self.count += 1
                return OutputHandler.HANDLED

        preview_handler = PreviewOutputHandler()
        total_files = 0

        # 统计sync命令将处理的文件数
        if auto_sync_var.get():
            preview_handler.count = 0  # 重置计数器
            p4_thread.handler = preview_handler
            p4_thread.run("sync", "-k", "-n", command_target)
            total_files += preview_handler.count

        if auto_sync_var.get():
            # 统计clean命令将处理的文件数
            preview_handler.count = 0  # 重置计数器
            p4_thread.handler = preview_handler
            p4_thread.run("clean", "-n", command_target)
            total_files += preview_handler.count

        if total_files == 0:
            total_files = 1

        # 显示并初始化进度条
        def show_progress_bar():
            progress_bar['value'] = 0
            progress_bar['maximum'] = 100
            progress_bar.grid()
            progress_label.grid()
            progress_percentage_label.configure(text="0%")
        root.after(0, show_progress_bar)

        # 使用新的Handler来更新进度条
        class MyOutputHandler(OutputHandler):
            def __init__(self):
                super().__init__()
                self.processed_files = 0

            def outputStat(self, stat):
                self.processed_files += 1
                update_progress(self.processed_files, total_files)
                log_message(f"{stat.get('depotFile', '')}")
                return OutputHandler.HANDLED

            def outputText(self, text):
                log_message(text)
                return OutputHandler.HANDLED

            def outputInfo(self, info):
                log_message(info)
                return OutputHandler.HANDLED

        handler = MyOutputHandler()
        p4_thread.handler = handler

        if auto_sync_var.get():
        # 实时同步操作并显示进度
            update_operation_label("正在链接文件...")
            log_message("开始执行 sync -k 命令...")
            p4_thread.run("sync", "-k", command_target)
            log_message("sync -k 命令已完成，文件状态更新完成。")

        if auto_clean_var.get():
            # 实时清理操作并显示进度
            update_operation_label("正在清理工作区...")
            log_message("开始执行 clean 命令...")
            p4_thread.run("clean", command_target)
            log_message("clean 命令已完成，工作区已清理。")

        update_operation_label("操作已完成。")

    except P4Exception as e:
        if "up-to-date" in str(e) or "no file(s) to reconcile" in str(e):
            log_message("文件已经是最新状态。")
        else:
            log_message("同步操作中发生错误：" + "\n".join(e.errors))
            raise  # 重新抛出错误，以便终止后续操作
    finally:
        p4_thread.disconnect()
        finish_sync_and_clean()

def finish_sync_and_clean():
    log_message("操作已完成。")
    # 隐藏进度条
    def hide_progress_bar():
        progress_bar.grid_remove()
        progress_label.grid_remove()
    root.after(0, hide_progress_bar)
    # 恢复UI控件
    enable_ui()

def switch_workspace():
    # 清空日志
    clear_log()

    target_workspace = p4_workspace_var.get()
    p4.client = p4_client_var.get()
    log_message(f"切换客户端为：{p4.client}")
    # 获取当前工作区配置
    client_spec = p4.fetch_client()
    # 修改流路径
    client_spec["Stream"] = select_stream_path
    log_message(f"切换流路径：{select_stream_path}")
    client_spec["Root"] = target_workspace
    log_message(f"切换工作区路径：{target_workspace}")
    # 保存更新后的工作区配置
    p4.save_client(client_spec)

    reset_default_var()

    # 禁用UI控件
    disable_ui()

    threading.Thread(target=run_sync_and_clean, daemon=True).start()

def disable_ui():
    # 禁用所有的输入控件和按钮
    for widget, default_state, default_fg in widgets_defaulte_settings:
        widget.configure(state='disabled')
        if default_fg != '':
            widget.configure(fg='grey')

def enable_ui():
    for widget, default_state, default_fg in widgets_defaulte_settings:
        widget.configure(state=default_state)
        if default_fg != '':
            widget.configure(fg=default_fg)

# 创建主窗口
root = tk.Tk()
root.title("Perforce流一键切换工具")

# 设置窗口默认尺寸为900×600
root.geometry("900x600")

# 使窗口可以拖拽缩放
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)

# 创建一个框架来容纳所有控件
frame = tk.Frame(root)
frame.grid(row=0, column=0, sticky='nsew')

# 设置框架的行和列权重
for i in range(15):
    frame.rowconfigure(i, weight=1)
frame.columnconfigure(1, weight=1)

row_index = 0

widgets_defaulte_settings = []

# 创建标签和文本框
p4_server_var = tk.StringVar()
p4_server_label = tk.Label(frame, text="服务器:")
p4_server_label.grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
p4_server_entry = tk.Entry(frame, textvariable=p4_server_var, state='readonly')
p4_server_entry.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
widgets_defaulte_settings.append([p4_server_entry, p4_server_entry.cget('state'), p4_server_entry.cget('fg')])

row_index += 1
pt_user_var = tk.StringVar()
pt_user_label = tk.Label(frame, text="用户:")
pt_user_label.grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
pt_user_entry = tk.Entry(frame, textvariable=pt_user_var,  state='readonly')
pt_user_entry.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
widgets_defaulte_settings.append([pt_user_entry, pt_user_entry.cget('state'), pt_user_entry.cget('fg')])

row_index += 1
# 创建客户端的下拉框，设置为只读
p4_client_var = tk.StringVar()
client_label = tk.Label(frame, text="流客户端:")
client_label.grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
client_combo = ttk.Combobox(frame, textvariable=p4_client_var, state='readonly')
client_combo.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
client_combo.bind("<Button-1>", update_client_combobox)
client_combo.bind("<<ComboboxSelected>>", select_client_combobox)
widgets_defaulte_settings.append([client_combo, client_combo.cget('state'), ''])

row_index += 1
# 创建项目的下拉框，设置为只读
p4_project_var = tk.StringVar()
project_label = tk.Label(frame, text="选择流项目:")
project_label.grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
project_combo = ttk.Combobox(frame, textvariable=p4_project_var, state='readonly')
project_combo.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
project_combo.bind("<Button-1>", update_project_combobox)
project_combo.bind("<<ComboboxSelected>>", select_project_combobox)
widgets_defaulte_settings.append([project_combo, project_combo.cget('state'), ''])

row_index += 1
# 创建分支的下拉框，设置为只读
p4_stream_var = tk.StringVar()
stream_label = tk.Label(frame, text="选择流分支:")
stream_label.grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
stream_combo = ttk.Combobox(frame, textvariable=p4_stream_var, state='readonly')
stream_combo.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
stream_combo.bind("<Button-1>", update_stream_combobox)
stream_combo.bind("<<ComboboxSelected>>", select_stream_combobox)
widgets_defaulte_settings.append([stream_combo, stream_combo.cget('state'), ''])

row_index += 1
# 工作区预览目录
p4_workspace_var = tk.StringVar()
workspace_label = tk.Label(frame, text="工作区目录:")
workspace_label.grid(row=row_index, column=0, padx=10, pady=5, sticky='e')
p4_workspace_entry = tk.Entry(frame, textvariable=p4_workspace_var)
p4_workspace_entry.grid(row=row_index, column=1, padx=10, pady=5, sticky='ew')
widgets_defaulte_settings.append([p4_workspace_entry, p4_workspace_entry.cget('state'), p4_workspace_entry.cget('fg')])

row_index += 1
# 创建"自动链接"复选框
auto_sync_var = tk.BooleanVar(value=True)  # 默认选中
auto_sync_check = tk.Checkbutton(frame, text="自动链接服务器文件", variable=auto_sync_var)
auto_sync_check.grid(row=row_index, column=1, sticky='w')
widgets_defaulte_settings.append([auto_sync_check, auto_sync_check.cget('state'), auto_sync_check.cget('fg')])

row_index += 1
# 创建"自动清理"复选框
auto_clean_var = tk.BooleanVar(value=True)  # 默认选中
auto_clean_check = tk.Checkbutton(frame, text="自动清理，注：该选项为强制清理所有文件，请谨慎选择", variable=auto_clean_var)
auto_clean_check.grid(row=row_index, column=1, sticky='w')
widgets_defaulte_settings.append([auto_clean_check, auto_clean_check.cget('state'), auto_clean_check.cget('fg')])

row_index += 1
# 添加"一键应用"按钮，放在中间
apply_button = tk.Button(frame, text="一键应用", command=switch_workspace)
apply_button.grid(row=row_index, column=0, columnspan=2, pady=10)
widgets_defaulte_settings.append([apply_button, apply_button.cget('state'), apply_button.cget('fg')])

row_index += 1
# 添加进度条和进度标签
progress_bar = ttk.Progressbar(frame, mode='determinate')
progress_label = tk.Frame(frame)
progress_label.grid_columnconfigure(0, weight=1)
progress_label.grid_columnconfigure(1, weight=1)
progress_label.grid_rowconfigure(0, weight=1)

operation_label = tk.Label(progress_label, text="", name='operation')
operation_label.grid(row=0, column=0, sticky='w')

progress_percentage_label = tk.Label(progress_label, text="0%", name='percentage')
progress_percentage_label.grid(row=0, column=1, sticky='e')

progress_bar.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
progress_label.grid(row=row_index+1, column=0, columnspan=2, sticky='ew')
# 默认隐藏进度条
progress_bar.grid_remove()
progress_label.grid_remove()

row_index += 2
# 添加日志输出区
log_label = tk.Label(frame, text="日志输出：")
log_label.grid(row=row_index, column=0, padx=10, pady=5, sticky='nw')

log_text = tk.Text(frame, height=10, state='disabled')
log_text.grid(row=row_index, column=1, padx=10, pady=5, sticky='nsew')

# 设置日志输出区的滚动条
scrollbar = tk.Scrollbar(frame, command=log_text.yview)
scrollbar.grid(row=row_index, column=2, sticky='ns')
log_text.configure(yscrollcommand=scrollbar.set)

# 调整日志输出区的行权重
frame.rowconfigure(row_index, weight=3)

try:
    p4 = P4()
    try:
        p4.connect()
    except P4Exception as e:
        messagebox.showerror("连接服务器失败", "请检查p4 set中P4PORT")
        sys.exit()

    log_message("成功连接到 P4 服务器！")

    p4_server_var.set(p4.port)
    pt_user_var.set(p4.user)

    local_stream_clients = get_local_stream_clients()
    if p4.client not in local_stream_clients:
        if len(local_stream_clients) > 0:
            p4.client = local_stream_clients[0]
        else:
            messagebox.showerror("未检测到流客户端", f"未在本地检测到用户{p4.user}所属的流客户端")
            sys.exit()

    p4_client_var.set(p4.client)

    select_client_combobox()

    # 启动主循环
    root.mainloop()
except P4Exception as e:
    # 捕获异常并获取报错信息
    if 'User' in str(e) and 'doesn\'t exist' in str(e):
         messagebox.showerror("用户设置错误", "请检查p4 set中P4USER")
    messagebox.showerror("程序运行错误", "\n".join(p4.errors))

    log_message("\n".join(p4.errors))
finally:
    if p4.connected():
        p4.disconnect()
        log_message("P4服务器已断开，请确保服务器正确开启后重启该软件")

#scopetest
import numpy as np
import os
import time
import matplotlib.pyplot as plt
import pyvisa
import datetime
import tkinter as tk
import threading
from tkinter import ttk,Label,Entry,PhotoImage
from PIL import Image, ImageTk
from time import strftime
image_label = None

# #2024/12，连接MDO34，输出截图
visa_address = 'TCPIP0::192.168.124.3::inst0::INSTR' #连接192.168.124.3的示波器
rm = pyvisa.ResourceManager()
scope = rm.open_resource(visa_address)
scope.timeout = 10000  # ms 超时
scope.write('*idn?')#示波器型号
print(scope.read())#返回示波器型号
scope.write('FILESystem:MOUNT:DRIve "I:;192.168.124.2;data;Administrator;123"')#挂载硬盘
#挂载需要增加判断，目前容易卡死
# timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")#随机设置文件名
# filename = f"H:data{timestamp}.bmp"
#filename1 = rf"E:\data\data{timestamp}.bmp"
# 定义常量
ERROR_MSG = "请输入有效的整数。"
#IMAGE_PATH = r"E:\data\data2.bmp"
RESIZE_DIMENSIONS = (600, 300)
LABEL_X_POS = 20
ENTRY_Y_OFFSET = 20
IMAGE_LABEL_X_POS = 170
IMAGE_LABEL_Y_POS = 100
BUTTON_TEXT = "查看示波器截图"
BUTTON_Y_POS = 500


def handle_enter_key(event, channel):#通道输入按键
    """
    处理回车键事件，尝试解析输入值，并基于通道生成命令输出。
    """
    user_input_str = event.widget.get()
    try:
        user_input_int = int(user_input_str)
        print(f"scope.write(f'CH{channel}:SCALE {user_input_int}E-03')")
        print(f"用户输入({channel}): {user_input_int}uV")
        scope.write(f'CH{channel}:SCALE {user_input_int}E-03')
    except ValueError:
        print(ERROR_MSG)

def create_entry_with_label(window, text, y_position, channel):#通道电压输入框
    """
    创建并放置带有标签的输入框，绑定回车事件。
    """
    label = tk.Label(window, text=text)
    label.place(x=LABEL_X_POS, y=y_position)
    entry = tk.Entry(window, width=10)
    entry.place(x=LABEL_X_POS, y=y_position + ENTRY_Y_OFFSET)
    entry.bind("<Return>", lambda event, ch=channel: handle_enter_key(event, ch))
    return entry


def load_and_resize_image(path, dimensions):#图片大小
    """
    加载图片并按指定尺寸调整大小。
    """
    img = Image.open(path)
    return img.resize(dimensions, Image.LANCZOS)


def insert_image():#按键显示图片
    """
    插入并显示图片，若已有图片则先删除。
    """
    global image_label
    if image_label:
        image_label.destroy()
    hdd_filename, local_filename = generate_unique_filename()# 生成新的图片文件名
    # 发送命令保存图片至新的文件名
    scope.write(f'SAVE:IMAGE "{hdd_filename}"')
    print("ok")
    if wait_for_file(local_filename):
        try:
            img_resized = load_and_resize_image(local_filename, RESIZE_DIMENSIONS)
        except FileNotFoundError:
            print("即使等待，图片文件仍未找到，请检查保存过程。")
            return

        photo = ImageTk.PhotoImage(img_resized)
        image_label = tk.Label(window, image=photo)
        image_label.image = photo
        image_label.place(x=IMAGE_LABEL_X_POS, y=IMAGE_LABEL_Y_POS)
    else:
        print(f"等待超时，未能找到文件 {filename1}。")

def check_and_insert_image_threaded():#线程
    """线程函数，用于检查文件并插入图片"""
    thread = threading.Thread(target=insert_image_thread_safe)
    thread.daemon = True  # 设置为守护线程，这样当主线程退出时，这个线程也会被终止
    thread.start()

def insert_image_thread_safe():#插入图片
    """线程安全的图片插入函数"""
    global image_label
    window.after(0, insert_image)  # 使用after方法来确保在Tkinter的主循环中执行GUI更新

def wait_for_file(local_filename, timeout=10):  # 图片等待时间 增加了超时参数，默认等待10秒
    """
    等待指定的文件出现，直到超时。

    :param local_filename: 等待的文件名（包含路径）
    :param timeout: 超时时间（秒）
    :return: 如果文件在超时时间内出现则返回True，否则返回False
    """
    start_time = time.time()  # 记录开始等待的时间
    while True:
        if os.path.exists(local_filename):  # 检查文件是否存在
            return True
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time > timeout:  # 判断是否超时
            print(f"等待文件'{local_filename}'超时。")
            return False
        time.sleep(1)  # 每秒检查一次，可以调整这个值以改变检查频率

def generate_unique_filename():#图片命名
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"I:data{timestamp}.bmp", rf"E:\data\data{timestamp}.bmp"

def on_window_close():
    try:
        scope.write('*cls')  # 清除示波器状态 #*ESR
        scope.close()  # 关闭与示波器的连接
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        rm.close()  # 尽管可能已经关闭，但仍尝试关闭资源管理器
        window.destroy()  # 确保窗口关闭

def toggle_channel_state(button_index):#按键开关通道
    """
    切换通道的开关状态，并根据状态更新按钮上的文本。
    """
    button = channel_buttons[button_index]
    is_on = button['text'] == '开'
    button.config(text='关' if is_on else '开')
    print(f"通道 CH{button_index + 1} {'已开启' if is_on else '已关闭'}")
    channel_str = f"CH{button_index + 1}"
    scope_command = f"SELECT:{channel_str} 1" if is_on else f"SELECT:{channel_str} 0"
    scope.write(scope_command)  # 确保 scope 对象已被正确定义并初始化
    print(f"向示波器发送命令: {scope_command}")
# 初始化一个列表来保存通道按钮
channel_buttons = []

def handle_channel_selection(event, var):
    """
    处理通道选择框的事件，当用户选择新的通道时，可以在这里添加逻辑。
    """
    selected_channel = var.get()
    print(f"用户选择了通道: {selected_channel}")
    # 这里可以根据需要添加更多处理逻辑，比如根据所选通道调整显示的设置等


# 初始化Tkinter窗口
window = tk.Tk()
window.title('Scope')
window.geometry('800x600')
# 绑定窗口关闭事件到自定义的清理函数
window.protocol("WM_DELETE_WINDOW", on_window_close)
# 创建输入框和标签
entries = [create_entry_with_label(window, f"CH{i}", i * 45 + 30, i)
    for i in range(1, 5)]
#选择带宽
selected_channel_var = tk.StringVar()
selected_channel_var.set("CH1")  # 默认选中CH1
channel_combobox = ttk.Combobox(window, textvariable=selected_channel_var, values=["CH1", "CH2", "CH3", "CH4"])
channel_combobox.place(x=LABEL_X_POS, y=5)  # 位置调整为适合你的界面布局
channel_combobox.bind("<<ComboboxSelected>>", lambda event: handle_channel_selection(event, selected_channel_var))

#通道开关选择
# 在创建输入框之后，为每个通道添加一个带有通道标记的开关按钮
for i in range(4):
    channel_name = f"CH{i + 1}"
    # 创建开关按钮，但不直接在按钮文本中加入通道标记，而是在回调中通过索引处理
    switch_button = tk.Button(window, text="开", command=lambda idx=i: toggle_channel_state(idx))
    switch_button.place(x=LABEL_X_POS + 80, y=i * 45 + ENTRY_Y_OFFSET + 75)  # 或使用适当布局管理器放置按钮，例如grid或place
    channel_buttons.append(switch_button)  # 将按钮添加到列表中以便在回调中引用
# ########创建查看图片按钮
button = tk.Button(window, text=BUTTON_TEXT, command=check_and_insert_image_threaded)
button.place(x=400, y=BUTTON_Y_POS)
# 进入主事件循环
window.mainloop()




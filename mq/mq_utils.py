import json
import os
import time

from conf import logger
import pyautogui as gui

try:
    from winsound import Beep
except:
    pass


def get_window(include=""):
    try:
        window = next(filter(lambda x: include in x.title, gui.getAllWindows()))
        return window
    except:
        logger.warning("当前未检测到软件窗口")


def activate_window(title):
    window = get_window(title)
    if not window:
        raise Exception("当前未检测到软件窗口")
    if window.isMinimized:
        window.restore()
    elif not window.isActive:
        try:
            window.activate()
        except:
            window.minimize()
            window.restore()
    window = get_window(title)
    if not window.isActive:
        raise Exception("激活窗口失败")
    return window


def screen_shot(window, save_path=""):
    im = gui.screenshot(region=(window.left, window.top, window.width, window.height))
    if save_path:
        im.save(save_path)
    return im


# 蜂鸣报警器，参数n为鸣叫次数，可用于提醒出错或任务完成
def alarm(n=2):
    for n in range(n):
        Beep(1500, 100)
        Beep(1500, 500)
        time.sleep(1.5)


def read_record(file_path):
    content = "{}"
    if os.path.exists(file_path):
        with open(file_path) as f:
            content = f.read() or content
    data = json.loads(content)
    return data


def write_record(file_path, data):
    last_data = read_record(file_path)
    last_data.update(data)
    with open(file_path, "w") as f:
        json.dump(last_data, f, indent=4)

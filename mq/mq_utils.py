import json
import os
import time

import conf
import pyautogui as gui

try:
    from winsound import Beep
except:
    pass


def get_window(include=conf.window):
    return next(filter(lambda x: include in x.title, gui.getAllWindows()))


window = get_window()


def screen_shot(save_path=""):
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

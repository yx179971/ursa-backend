import json
import os
import re
import time
import uuid

import conf
from conf import db
import models
from mq import mq_utils
from mq.mq_utils import screen_shot
from pynput import mouse
from schemas import Action
from schemas import Node
from utils import redis_utils

from .base import Executor


class Recorder(Executor):
    def __init__(self, job_id, uuid_=None):
        self.job = db.query(models.Job).filter(models.Job.id == job_id).first().get()
        self.window = mq_utils.activate_window(self.job.config.get("window"))
        self.uuid = uuid_ or uuid.uuid4().hex
        self.img_dir = os.path.join(conf.img_dir, self.uuid)
        os.makedirs(self.img_dir, exist_ok=True)
        self.click_point = 0, 0
        self.click_right = False
        self.scroll_up = 0
        self.shot_lock = False

    def on_move(self, img_path):
        def inner(x, y):
            if not self.shot_lock:
                self.shot_lock = True
                screen_shot(self.window, img_path)
                return False

        return inner

    def on_click(self):
        def inner(x, y, button, pressed):
            if pressed:
                x -= self.window.left
                y -= self.window.top
                self.click_point = x, y
                self.scroll_up = 0
                if button == mouse.Button.right:
                    self.click_right = True
                else:
                    self.click_right = False
                return False

        return inner

    def on_scroll(self):
        def inner(x, y, dx, dy):
            x -= self.window.left
            y -= self.window.top
            self.click_point = x, y
            self.scroll_up = dy
            return False

        return inner

    def start(self):
        n = 0
        uid = uuid.uuid4().hex
        while True:
            self.check_signal()
            if not self.window.isActive:
                time.sleep(0.25)
                continue

            img_path = os.path.join(self.img_dir, f"record_{uid}_{n:03}.png")
            # 移动的时候截一张图
            with mouse.Listener(on_move=self.on_move(img_path)) as listener:
                listener.join()
            self.shot_lock = False

            # 点击的时候标注位置
            with mouse.Listener(
                on_click=self.on_click(),
                on_scroll=self.on_scroll(),
            ) as listener:
                listener.join()
            # 切换到其他窗口暂停录制
            if not self.window.isActive:
                os.remove(img_path)
                continue
            else:
                os.rename(
                    img_path,
                    img_path.replace(
                        ".png",
                        f"_{self.click_point[0]}_{self.click_point[1]}_{self.scroll_up}.png",
                    ),
                )

            n += 1

    def trans_to_job(self):
        all_nodes = {}
        for img_name in os.listdir(self.img_dir):
            num, x, y, action = re.match(
                r"record_.*?_(\d+)_(\d+)_(\d+)_(.*).png", img_name
            ).groups()
            try:
                scroll_up = int(action)
            except:
                scroll_up = None
            node = Node(
                id=str(uuid.uuid4()),
                name=f"录制节点{num}",
                rect={"x": int(x) - 10, "y": int(y) - 10, "w": 20, "h": 20},
                background=os.path.join(self.uuid, img_name),
                action=Action.click_area,
                scroll_up=scroll_up,
                click_right=action == "right",
            )
            all_nodes[node.id] = node

        data = {"nodes": [], "edges": []}
        last_node = None
        for node in sorted(list(all_nodes.values()), key=lambda x: x.background):
            data["nodes"].append(json.loads(node.json()))
            if last_node:
                data["edges"].append(
                    {
                        "source": last_node.id,
                        "target": node.id,
                    }
                )
            last_node = node

        with open(conf.data_path, "w") as f:
            json.dump(data, f)

        redis_utils.set_mq("status", models.MqStatus.finish.name)

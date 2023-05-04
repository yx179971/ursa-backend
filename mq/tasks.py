from collections import deque
import copy
import logging
import os
import random
import shutil
import threading
from threading import Thread
import time

from celery import Celery
import conf
from conf import db
import cv2
import models
from mq import settings
from mq import utils
import numpy as np
import pyautogui as gui

app = Celery("tasks", broker="redis://192.168.31.112:6379/0")
app.conf.imports = ("mq.tasks",)
app.conf.worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s %(filename)s %(funcName)s %(lineno)s] %(message)s"


def get_node_config(job_id):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    config = job.config
    nodes = [
        models.Node(
            id=node["id"],
            name=node["attrs"]["text"]["text"],
            action=node.get("data", {}).get("action", "pass"),
            img_url=node.get("data", {}).get("img_url"),
            accuracy=node.get("data", {}).get("accuracy"),
            position=node.get("data", {}).get("position"),
            interval=node.get("data", {}).get("interval"),
        )
        for node in filter(lambda x: x["shape"] != "edge", config["cells"])
    ]
    edges = [
        models.Edge(
            id=edge["id"],
            source=edge["source"]["cell"],
            target=edge["target"]["cell"],
        )
        for edge in filter(lambda x: x["shape"] == "edge", config["cells"])
    ]
    return nodes, edges


@app.task
def job_run(job_id):
    nodes, edges = get_node_config(job_id)
    Controller(nodes, edges).loop()


class Timer:
    def __init__(self, interval):
        self.interval = interval
        self.end = False
        self.start()

    def start(self):
        time.sleep(self.interval)
        self.end = True


class Controller:
    def __init__(self, nodes, edges, interval=1, interval_floating=0.5):
        self.nodes = nodes
        self.edges = edges
        work_dir = os.path.dirname(os.path.abspath(__file__))
        self.save_path = os.path.join(work_dir, "screenshots")
        self.template_path = conf.img_dir
        # self.record_path = os.path.join(game_dir, "record.json")

        self.templates = None
        self.screen = None
        self.window = utils.mumu
        self.custom_accuracy = {}
        # self.stage = ""

        # 延时
        self.interval = interval
        self.interval_floating = interval_floating
        self.timer = None

        self.act_cls_list = []
        # self.record = None
        # self.init_acts = []
        # 截图
        self.log_screen_rotate = -1
        self.log_screen = []

        self.init()

    def init(self):
        self.templates = self.load_template()
        shutil.rmtree(self.save_path, ignore_errors=True)
        os.makedirs(self.save_path, exist_ok=True)
        # self.record = self.load_record()

    #     if self.record:
    #         module = importlib.import_module(f"game.{self.game_name}.action")
    #         self.init_acts = [
    #             getattr(module, act_cls) for act_cls in self.record.get("act_cls_list", [])
    #         ]
    #         if self.record.get("stage"):
    #             stage_cls, stage = self.record["stage"].split(".")
    #             self.stage = getattr(getattr(module, stage_cls), stage)
    #     else:
    #         self.record = {"completed_stage": []}
    #
    # def load_record(self):
    #     return utils.read_record(self.record_path)
    #
    # def save_record(self, data):
    #     utils.write_record(self.record_path, data)
    #
    # def on_except(self):
    #     self.record.update(
    #         {
    #             "stage": str(self.stage),
    #             "act_cls_list": [act_cls.__name__ for act_cls in self.act_cls_list],
    #         }
    #     )
    #     self.save_record(self.record)

    def load_template(self):
        imgs = {}
        for node in self.nodes:
            if node.img_url:
                img_url = os.path.join(self.template_path, node.img_url)
                imgs[node.img_url] = [
                    cv2.imread(img_url),
                    node.accuracy or settings.accuracy,
                ]
        return imgs

    def move_to(self, left, right, top, bottom):
        gui.moveTo(
            random.uniform(
                self.window.left + left * self.window.width,
                self.window.left + right * self.window.width,
            ),
            random.uniform(
                self.window.top + top * self.window.height,
                self.window.top + bottom * self.window.height,
            ),
        )

    def cap(self):
        save_path = ""
        # if self.log_screen_rotate != 0:
        #     img_name = f"{datetime.now().strftime('%m_%d_%H_%M_%S')}.png"
        #     save_path = os.path.join(self.save_path, img_name)

        self.screen = cv2.cvtColor(
            np.array(utils.screen_shot(save_path)), cv2.COLOR_BGR2RGB
        )
        # if self.log_screen_rotate > 0:
        #     self.log_screen.append((save_path, self.screen))

    # def __del__(self):
    #     if self.log_screen_rotate > 0:
    #         for save_path, screen in self.log_screen:
    #             cv2.imwrite(save_path, screen)

    @staticmethod
    def random_offset(p, w=40, h=20):
        a, b = p
        w, h = int(w / 3), int(h / 3)
        c, d = random.randint(-w, w), random.randint(-h, h)
        e, f = a + c, b + d
        return e, f

    @staticmethod
    def random_delay(x=0.3, y=1):
        t = random.uniform(x, y)
        time.sleep(t)

    @staticmethod
    def show_window(msg, screen):
        Thread(target=utils.alarm).start()
        cv2.imshow(msg, screen)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def locate(self, target, double=False, double_sleep=1, show=False):
        self.stop_check()
        logging.info(
            f"目标:{target}",
        )
        wanted = self.templates[target]
        loc_pos = []
        wanted, treshold = wanted
        result = cv2.matchTemplate(self.screen, wanted, cv2.TM_CCOEFF_NORMED)
        location = np.where(result >= treshold)

        h, w = wanted.shape[:-1]

        n, ex, ey = 1, 0, 0
        display = copy.deepcopy(self.screen)
        for pt in zip(*location[::-1]):
            x, y = pt[0] + int(w / 2), pt[1] + int(h / 2)
            if (x - ex) + (y - ey) < 15:  # 去掉邻近重复的点
                continue
            ex, ey = x, y

            cv2.circle(display, (x, y), 10, (0, 0, 255), 3)

            x, y = int(x), int(y)
            loc_pos.append([x, y])

        if settings.debug or show:  # 在图上显示寻找的结果，调试时开启
            self.show_window(f"we {'' if loc_pos else 'not'} get", display)

        if loc_pos:
            logging.debug(f"Y 已找到目标 {target}")
        else:
            logging.warning(
                f"N 未找到目标 {target}",
            )
        if loc_pos and double:
            time.sleep(double_sleep)
            return self.locate(target)
        return loc_pos

    def stop_check(self):
        c_x, c_y = gui.position()
        if c_x == 0 and c_y == 0:
            raise Exception("stop by manual")

    def _click(self, x, y, simple=False):
        logging.debug(f"{x, y}")
        self.stop_check()
        gui.moveTo(x, y)
        if simple:
            gui.click(x, y)
        else:
            gui.mouseDown(x, y, button=gui.LEFT)
            time.sleep(random.uniform(0.1, 0.3))
            gui.mouseUp(x, y, button=gui.LEFT)

    def click_current(self, *args, **kwargs):
        x, y = gui.position()
        self._click(x, y, *args, **kwargs)

    def click(self, target, ignore=True, simple=False, sleep=0):
        wanted = self.templates[target]
        size = wanted[0].shape
        h, w, _ = size
        pts = self.locate(target)
        if pts:
            xx = pts[0]
            x, y = self.random_offset(xx, w, h)
            x += self.window.left
            y += self.window.top
            self._click(x, y, simple)
            self.random_delay()
            if sleep:
                time.sleep(sleep)
            return True
        else:
            if not ignore:
                raise Exception(f"not find target: {target}")
            return False

    def set_timer(self, interval):
        with threading.Lock():
            self.timer = Timer(interval)

    def delay(self):
        with threading.Lock():
            if self.timer and self.timer.end or not self.timer:
                interval = random.uniform(
                    self.interval - self.interval_floating,
                    self.interval + self.interval_floating,
                )
                self.timer = Timer(interval)

        while not self.timer.end:
            pass

    def get_start_node(self):
        all_target = set(edge.target for edge in self.edges)
        return next(filter(lambda x: x.id not in all_target, self.nodes))

    def act_pass(self, node):
        return True

    def act_click_area(self, node):
        self.move_to(**node.position)
        self.click_current()
        return True

    def act_click_target(self, node):
        return self.click(node.img_url)

    def loop(self):
        q = deque([self.get_start_node()])

        while q:
            if not self.window.isActive:
                time.sleep(1)
                continue
            node = q.pop()

            logging.info(node.name)

            if node.action != "pass":
                self.cap()
                if not self.locate(node.img_url):
                    q.appendleft(node)
                    self.delay()
                    continue

                action = getattr(self, f"act_{node.action or 'click_target'}")
                if not action(node):
                    q.append(node)
                    self.delay()
                    continue

            next_ids = set(
                edge.target
                for edge in filter(lambda x: x.source == node.id, self.edges)
            )
            q = deque(list(filter(lambda x: x.id in next_ids, self.nodes)))

            interval = node.interval
            if interval is not None:
                self.set_timer(interval)
            self.delay()


if __name__ == "__main__":
    job_run(1)

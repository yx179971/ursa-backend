from collections import deque
import copy
from datetime import datetime
import os
import random
import shutil
import threading
from threading import Thread
import time
import uuid

import conf
from conf import db
from conf import logger
import cv2
import models
from mq import mq_utils
import numpy as np
import pyautogui as gui
import schemas
from schemas import Action
from utils import redis_utils

from .base import Executor


class Timer:
    def __init__(self, interval):
        self.interval = interval
        self.end = False
        self.start()

    def start(self):
        time.sleep(self.interval)
        self.end = True


class Controller(Executor):
    def __init__(
        self,
        job_id,
        uuid_=None,
        interval=1,
        interval_floating=0.5,
        node_track=None,
        start_node_id="",
    ):
        self.uuid = uuid_ or uuid.uuid4().hex
        self.job = db.query(models.Job).filter(models.Job.id == job_id).first().get()
        self.start_node_id = start_node_id
        self.nodes, self.edges = self.get_node_config(job_id)
        work_dir = os.path.dirname(os.path.abspath(__file__))
        self.save_path = os.path.join(work_dir, "screenshots")
        self.template_path = conf.img_dir
        # self.record_path = os.path.join(game_dir, "record.json")

        self.templates = None
        self.screen = None
        self.window = self.init_window()
        time.sleep(1)
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
        self.node_track = node_track or []

    def init_window(self):
        window = mq_utils.activate_window(self.job.config.get("window"))
        start = self.job.config.get("window_start")
        wh = self.job.config.get("window_width_height")
        logger.info(start)
        logger.info(wh)
        if start:
            window.moveTo(*list(map(int, start.split(","))))
        if wh:
            window.resizeTo(*list(map(int, wh.split(","))))
        return window

    def get_node_config(self, job_id):
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        config = job.config
        nodes = []
        for node in filter(lambda x: x["shape"] != "edge", config["cells"]):
            data = node.get("data", {})
            data["id"] = node["id"]
            data["name"] = node["attrs"]["text"]["text"]
            data["rank"] = node["attrs"].get("rank", {}).get("text")
            data["context"] = {"job_id": self.job.id}
            nodes.append(
                schemas.Node(**{k: v for k, v in data.items() if v is False or v})
            )
        edges = [
            schemas.Edge(
                id=edge["id"],
                source=edge["source"]["cell"],
                target=edge["target"]["cell"],
            )
            for edge in filter(lambda x: x["shape"] == "edge", config["cells"])
        ]
        return nodes, edges

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
            for s in ["locate", "target"]:
                img_url = getattr(node, s)
                if img_url:
                    img_path = os.path.join(self.template_path, img_url)
                    imgs[img_url] = [
                        cv2.imread(img_path),
                        getattr(node, f"{s}_accuracy") or conf.accuracy,
                    ]
        return imgs

    def move_to(self, x, y, w, h):
        move_to = (
            random.uniform(
                self.window.left + x,
                self.window.left + x + w,
            ),
            random.uniform(
                self.window.top + y,
                self.window.top + y + h,
            ),
        )
        if conf.mq_debug:
            display = copy.deepcopy(self.screen)
            cv2.circle(display, (x, y), 10, (0, 0, 255), 3)
            self.show_window(f"{move_to}", display)
        gui.moveTo(move_to)

    def cap(self):
        save_path = ""
        # if self.log_screen_rotate != 0:
        #     img_name = f"{datetime.now().strftime('%m_%d_%H_%M_%S')}.png"
        #     save_path = os.path.join(self.save_path, img_name)

        self.screen = cv2.cvtColor(
            np.array(mq_utils.screen_shot(self.window, save_path)), cv2.COLOR_BGR2RGB
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
        Thread(target=mq_utils.alarm).start()
        cv2.imshow(msg, screen)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def locate(self, target, double=False, double_sleep=1, show=False, rect=None):
        self.stop_check()
        wanted = self.templates[target]
        loc_pos = []
        wanted, threshold = wanted
        result = cv2.matchTemplate(self.screen, wanted, cv2.TM_CCOEFF_NORMED)
        location = np.where(result >= threshold)

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
            if rect and not (
                rect["x"] < x < rect["x"] + rect["w"]
                and rect["y"] < y < rect["h"] + rect["y"]
            ):
                continue
            loc_pos.append([x, y])

        if conf.mq_debug or show:  # 在图上显示寻找的结果，调试时开启
            self.show_window(f"we {'' if loc_pos else 'not'} get", display)

        if loc_pos:
            logger.info(f"Y 已找到目标 {target}")
        else:
            logger.warning(
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

    def _click(self, x, y, simple=False, right=False):
        logger.debug(f"{x, y}")
        self.stop_check()
        gui.moveTo(x, y)
        button = right and gui.RIGHT or gui.PRIMARY
        if simple:
            gui.click(x, y, button=button)
        else:
            gui.mouseDown(x, y, button=button)
            time.sleep(random.uniform(0.05, 0.1))
            gui.mouseUp(x, y, button=button)

    def click_current(self, *args, **kwargs):
        x, y = gui.position()
        self._click(x, y, *args, **kwargs)

    def click(self, target, ignore=True, simple=False, sleep=0, rect=None, right=False):
        wanted = self.templates[target]
        size = wanted[0].shape
        h, w, _ = size
        pts = self.locate(target, rect=rect)
        if pts:
            xx = pts[0]
            x, y = self.random_offset(xx, w, h)
            x += self.window.left
            y += self.window.top
            self._click(x, y, simple, right=right)
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
        if self.start_node_id:
            nodes = list(
                filter(
                    lambda node: node.id == self.start_node_id,
                    self.nodes,
                )
            )
        else:
            nodes = list(
                filter(
                    lambda node: node.type == schemas.NodeType.start and node.enable,
                    self.nodes,
                )
            )
        if not nodes:
            all_target = set(edge.target for edge in self.edges)
            nodes = list(
                filter(
                    lambda node: node.id not in all_target and node.enable, self.nodes
                )
            )
        if len(nodes) > 1:
            raise Exception("只能有一个起点")
        elif not nodes:
            raise Exception(f"未知的节点id: {self.start_node_id}")
        else:
            return nodes[0]

    def act_pass(self, node):
        return True

    def act_click_area(self, node):
        self.move_to(node.rect["x"], node.rect["y"], node.rect["w"], node.rect["h"])
        try:
            scroll_up = int(node.scroll_up)
        except:
            scroll_up = 0
        if scroll_up == 0:
            self.click_current(right=node.click_right)
        else:
            gui.scroll(scroll_up * 200)
        return True

    def act_click_locate(self, node):
        # todo: 优化二次定位
        return self.click(node.locate, rect=node.locate_rect, right=node.click_right)

    def act_click_target(self, node):
        return self.click(node.target, right=node.click_right)

    def node_check(self, node):
        if not node.locate:
            raise Exception(f"节点必须有检测目标")

    def log_node(self, node):
        job = models.JobLog(
            uuid=self.uuid,
            job_id=self.job.id,
            node_id=node.id,
            create_time=datetime.now(),
        )
        db.add(job)
        db.commit()

    def check_reload(self):
        job = db.query(models.Job).filter(models.Job.id == self.job.id).first()
        logger.info(job.map_signature)
        logger.info(self.job.map_signature)
        if job.map_signature != self.job.map_signature:
            self.job = job.get()
            self.nodes, self.edges = self.get_node_config(self.job.id)
            self.templates = self.load_template()

    def get_next_nodes(self, node):
        next_nodes = []
        next_ids = set(
            edge.target for edge in filter(lambda x: x.source == node.id, self.edges)
        )
        for n in self.nodes:
            if n.id not in next_ids or not n.enable:
                continue
            if n.exec_count:
                exec_count = (
                    db.query(models.JobLog)
                    .filter(
                        models.JobLog.uuid == self.uuid,
                        models.JobLog.job_id == self.job.id,
                        models.JobLog.node_id == n.id,
                    )
                    .count()
                )
                if exec_count >= n.exec_count:
                    continue
            next_nodes.append(n)
        next_nodes.sort(key=lambda x: x.rank or 0, reverse=True)
        if next_nodes and node.type == schemas.NodeType.operation:
            # 有后续节点才需要重试
            next_nodes.insert(0, node)
        return next_nodes

    def set_node_track(self):
        redis_utils.set_mq(
            "node_track",
            "->".join(
                [f"{node.context['job_id']}/{node.name}" for node in self.node_track]
            ),
        )

    def loop(self):
        node = None
        start_node = self.get_start_node()
        q = deque()

        while True:
            self.check_signal()
            if not self.window.isActive:
                time.sleep(1)
                continue

            if not node:
                self.cap()
                q.extend([start_node])
            else:
                self.node_track.pop()

            if not q:
                self.cap()
                self.check_reload()
                q.extend(self.get_next_nodes(start_node))
            if not q:
                break

            # 先执行右侧队尾
            node = q.pop()
            # todo: 假死报警
            self.node_track.append(node)
            self.set_node_track()
            logger.info(node.name)

            if node.type == schemas.NodeType.job:
                Controller(
                    node.job_id, uuid_=self.uuid, node_track=self.node_track
                ).loop()
            elif node.type == schemas.NodeType.operation:
                self.node_check(node)
                if not self.locate(node.locate, rect=node.locate_rect):
                    if not q:
                        self.delay()
                    continue

                if node.action != Action.pass_:
                    action = getattr(self, f"act_{node.action.value}")
                    if not action(node):
                        q.append(node)
                        self.delay()
                        continue

            # 执行完毕
            self.log_node(node)
            q.clear()
            start_node = node
            # 执行后延时
            interval = node.delay
            if interval is not None:
                self.set_timer(interval)
            self.delay()

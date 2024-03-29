import ctypes
from multiprocessing import freeze_support
from multiprocessing import Manager
from multiprocessing import Process
import os.path
import subprocess
import sys
import time
import traceback

import conf
from conf import logger
from mq import tasks
from utils import redis_utils
import web


def web_server(share_dict):
    redis_utils.r = share_dict
    while True:
        try:
            web.main()
        except:
            logger.error(traceback.format_exc())


def worker(share_dict):
    redis_utils.r = share_dict
    tasks.main()


def front():
    return subprocess.Popen([os.path.join(conf.base_dir, conf.front_exe)])


if __name__ == "__main__":
    freeze_support()
    ctypes.windll.kernel32.SetConsoleTitleW("Ursa后台服务请勿关闭")
    conf.mode = conf.SINGLE_MODE
    share_dict = Manager().dict()
    web_process = Process(target=web_server, args=(share_dict,), daemon=True)
    worker_process = Process(target=worker, args=(share_dict,), daemon=True)
    web_process.start()
    worker_process.start()
    if sys.argv[-1] != "backend":
        front_process = front()
        while front_process.poll() is None:
            time.sleep(1)
    else:
        while True:
            pass
    logger.info("frontend closed")

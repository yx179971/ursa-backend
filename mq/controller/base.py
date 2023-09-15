import time

from conf import logger
import models
from utils import redis_utils
from utils.exception import BreakException
from utils.exception import CancelException


class Executor:
    @staticmethod
    def check_signal():
        while True:
            signal = redis_utils.get_mq().signal
            logger.info(f"signal-----------------{signal.name}")
            if signal == models.MqSignal.running:
                redis_utils.set_mq("status", models.MqStatus.running.name)
            elif signal == models.MqSignal.stopping:
                redis_utils.set_mq("status", models.MqStatus.stopping.name)
                raise BreakException
            elif signal == models.MqSignal.cancel:
                redis_utils.set_mq("status", models.MqStatus.stopping.name)
                raise CancelException
            elif signal == models.MqSignal.pause:
                redis_utils.set_mq("status", models.MqStatus.pause.name)
                time.sleep(1)
                continue
            break

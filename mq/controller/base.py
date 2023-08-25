import logging
import time

import models
from utils import redis_utils
from utils.exception import BreakException
from utils.exception import CancelException


class Executor:
    def check_signal(self):
        while True:
            signal = redis_utils.get_mq().signal
            logging.info(f"signal-----------------{signal.name}")
            if signal == models.MqSignal.stopping:
                redis_utils.set_mq("status", models.MqStatus.stopping.name)
                raise BreakException
            elif signal == models.MqSignal.cancel:
                redis_utils.set_mq("status", models.MqStatus.stopping.name)
                raise CancelException
            elif signal == models.MqSignal.pause:
                redis_utils.set_mq("status", models.MqStatus.pause.name)
                time.sleep(1)
                continue
            if hasattr(self, "node_track"):
                redis_utils.set_mq(
                    "node_track",
                    "->".join(
                        [
                            f"{node.context['job_id']}/{node.name}"
                            for node in self.node_track
                        ]
                    ),
                )
            break

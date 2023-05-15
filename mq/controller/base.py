import models
from utils import redis_utils
from utils.exception import BreakException
from utils.exception import CancelException


class Executor:
    def check_signal(self):
        signal = redis_utils.get_mq().signal
        print(f"signal-----------------{signal.name}")
        if signal == models.MqSignal.stopping:
            redis_utils.set_mq("status", models.MqStatus.stopping.name)
            raise BreakException
        elif signal == models.MqSignal.cancel:
            redis_utils.set_mq("status", models.MqStatus.stopping.name)
            raise CancelException
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

from celery import Celery
from celery import signals
import conf
import models
from mq.controller import Controller
from mq.controller import Recorder
from utils import redis_utils
from utils.exception import BreakException
from utils.exception import CancelException

app = Celery("tasks", broker=f"redis://{conf.REDIS_HOST}:{conf.REDIS_PORT}/0")
app.conf.imports = ("mq.tasks",)
app.conf.worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s %(filename)s %(funcName)s %(lineno)s] %(message)s"


@signals.worker_ready.connect
def reset_redis_status(*args, **kwargs):
    redis_utils.set_mq("signal", models.MqSignal.ready.name)
    redis_utils.set_mq("status", models.MqStatus.stopped.name)


@app.task
def job_run(job_id, node_id=""):
    redis_utils.set_mq("job_id", job_id)
    try:
        Controller(job_id, start_node_id=node_id).loop()
    except (BreakException, CancelException):
        redis_utils.set_mq("status", models.MqStatus.stopped.value)
    except Exception as e:
        redis_utils.set_mq("status", models.MqStatus.failure.value)
        raise e
    redis_utils.set_mq("status", models.MqStatus.stopped.value)


@app.task
def record_start(job_id):
    redis_utils.set_mq("job_id", job_id)
    recorder = Recorder()
    try:
        recorder.start()
    except BreakException:
        recorder.trans_to_job()
    except (BreakException, CancelException):
        redis_utils.set_mq("status", models.MqStatus.stopped.value)
    except Exception as e:
        redis_utils.set_mq("status", models.MqStatus.failure.value)
        raise e


if __name__ == "__main__":
    job_run(1)

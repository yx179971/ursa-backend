import time

from celery import Celery
from celery import signals
import conf
import models
from mq.controller import Controller
from mq.controller import Recorder
from utils import redis_utils
from utils.exception import BreakException
from utils.exception import CancelException


@signals.worker_ready.connect
def reset_redis_status(*args, **kwargs):
    redis_utils.set_mq("signal", models.MqSignal.ready.name)
    redis_utils.set_mq("status", models.MqStatus.stopped.name)


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


if conf.mode == conf.CLUSTER_MODE:
    app = Celery("tasks", broker=f"redis://{conf.REDIS_HOST}:{conf.REDIS_PORT}/0")
    app.conf.imports = ("mq.tasks",)
    app.conf.worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s %(filename)s %(funcName)s %(lineno)s] %(message)s"
    job_run = app.task(job_run)
    record_start = app.task(record_start)
else:
    app = None


def send_job_run(job_id, node_id=""):
    if conf.mode == conf.SINGLE_MODE:
        redis_utils.set_mq("worker_func", "job_run")
        redis_utils.set_mq("job_id", job_id)
        redis_utils.set_mq("node_id", node_id)
    else:
        job_run(job_id, node_id).delay()


def send_record_start(job_id):
    if conf.mode == conf.SINGLE_MODE:
        redis_utils.set_mq("worker_func", "record_start")
        redis_utils.set_mq("job_id", job_id)
    else:
        record_start(job_id).delay()


def main():
    while True:
        worker_func = redis_utils.r.get("worker_func")
        reset_redis_status()
        if worker_func:
            job_id = redis_utils.r["job_id"]
            node_id = redis_utils.r["node_id"]
            globals()[worker_func](job_id, node_id)
            redis_utils.set_mq("worker_func", "")
        print("worker alive")
        time.sleep(1)


if __name__ == "__main__":
    job_run(1)

import conf
import redis
import schemas

r = redis.Redis(host=conf.REDIS_HOST, port=conf.REDIS_PORT, decode_responses=True)

mq_key = "mq"


class Lock:
    def __init__(self, key):
        self.key = key

    def __enter__(self):
        if r.incr(self.key) != 1:
            raise Exception(f"{self.key} locked!!!")

    def __exit__(self, exc_type, exc_val, exc_tb):
        r.delete(self.key)


def get_mq():
    return schemas.Mq(**r.hgetall(mq_key))


def set_mq(key, value):
    r.hset(mq_key, key, value)

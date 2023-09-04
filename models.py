from enum import auto
from enum import Enum

from conf import Base
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String


class MqSignal(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    running = auto()
    stopping = auto()
    pause = auto()
    reload = auto()
    cancel = auto()


class MqStatus(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    running = auto()
    pause = auto()
    stopping = auto()
    stopped = auto()
    finish = auto()
    failure = auto()

    def end_set(self):
        return {self.stopped.name, self.finish.name, self.failure.name}


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    config = Column(JSON, default=dict)
    sort = Column(Integer, default=0)
    map_signature = Column(String)

    def get(self):
        return Job(
            **{k: v for k, v in self.__dict__.items() if k in Job.__mapper__.c.keys()}
        )


class JobLog(Base):
    __tablename__ = "job_log"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, index=True)
    job_id = Column(Integer, index=True)
    node_id = Column(String)
    create_time = Column(DateTime)

from enum import auto
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from models import MqSignal
from models import MqStatus
from pydantic import BaseModel


class JobBase(BaseModel):
    name: str


class JobCreate(JobBase):
    pass


class Job(JobBase):
    id: int
    config: Dict
    sort: int = 0

    class Config:
        orm_mode = True


class JobResponse(BaseModel):
    data: Job


class JobListResponse(BaseModel):
    data: List[Job]


class JobListRequest(BaseModel):
    data: List[Job]


class JobRunRequest(BaseModel):
    node_id: Optional[str]
    force: bool = False


class SuccessResponse(BaseModel):
    success: bool = True


class Action(Enum):
    def _generate_next_value_(name, start, count, last_values):
        if name == "pass_":
            return "pass"
        return name

    pass_ = auto()
    click_locate = auto()
    click_target = auto()
    click_area = auto()


class NodeType(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    job = auto()
    operation = auto()
    start = auto()
    virtual = auto()


class Node(BaseModel):
    id: str
    name: str
    enable: bool = True
    action: Optional[Action]
    click_right: bool = False
    rank: Optional[int]
    exec_count: Optional[int]
    background: Optional[str]
    locate: Optional[str]
    locate_rect: Optional[Dict]
    locate_accuracy: Optional[float]
    target: Optional[str]
    target_accuracy: Optional[float]
    rect: Optional[Dict]
    scroll_up: Optional[int]
    delay: Optional[int]
    type: NodeType = NodeType.operation
    job_id: Optional[int]
    context: Optional[Dict]


class Edge(BaseModel):
    id: str
    source: str
    target: str


class Mq(BaseModel):
    job_id: Optional[int]
    node_id: Optional[str]
    status: Optional[MqStatus]
    signal: Optional[MqSignal]
    node_track: Optional[str]
    worker_func: Optional[str]


class MqResponse(BaseModel):
    data: Mq

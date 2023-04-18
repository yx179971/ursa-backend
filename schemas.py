from typing import List, Dict, Union

from pydantic import BaseModel


class JobBase(BaseModel):
    name: str


class JobCreate(JobBase):
    pass


class Job(JobBase):
    id: int
    config: Dict

    class Config:
        orm_mode = True

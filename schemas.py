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


class JobResponse(BaseModel):
    data: Job


class JobListResponse(BaseModel):
    data: List[Job]


class SuccessResponse(BaseModel):
    success: bool = True

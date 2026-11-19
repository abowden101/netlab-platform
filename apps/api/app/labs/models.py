"""Pydantic schemas for the labs API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ObjectiveOut(BaseModel):
    id: str
    title: str
    description: str = ""
    engine: str
    node: str


class LabOut(BaseModel):
    id: str
    title: str
    description: str = ""
    estimated_minutes: int = 45
    objectives: list[ObjectiveOut] = []


class LabDetailOut(LabOut):
    guide: str = ""


class SessionCreate(BaseModel):
    lab_slug: str
    ttl_seconds: int | None = None


class SessionOut(BaseModel):
    id: str
    lab_slug: str
    status: str
    created_at: datetime | None = None
    expires_at: datetime | None = None
    queue_position: int | None = None

    model_config = ConfigDict(from_attributes=True)


class NodeOut(BaseModel):
    name: str
    kind: str
    image: str
    status: str = "unknown"


class LinkOut(BaseModel):
    from_node: str
    to_node: str


class SessionDetailOut(SessionOut):
    nodes: list[NodeOut] = []
    links: list[LinkOut] = []


class SnapshotOut(BaseModel):
    session_id: str
    configs: dict[str, str]

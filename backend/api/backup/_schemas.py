"""Pydantic models for the backup API."""
from pydantic import BaseModel, Field


class BackupRequest(BaseModel):
    components: dict = Field(default_factory=dict)
    label: str = ""


class RestoreRequest(BaseModel):
    filename: str
    components: dict = Field(default_factory=dict)


class RetentionRequest(BaseModel):
    days: int  # 0 = disabled, negative = max number of backups


class SetDirectoryRequest(BaseModel):
    path: str

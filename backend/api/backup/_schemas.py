"""Pydantic models for the backup API."""
from pydantic import BaseModel, ConfigDict, Field


class BackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    components: dict = Field(default_factory=dict)
    label: str = ""


class RestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    components: dict = Field(default_factory=dict)


class RetentionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days: int  # 0 = disabled, negative = max number of backups


class SetDirectoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str

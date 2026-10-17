"""Pydantic models for the backup API."""
from pydantic import BaseModel, ConfigDict, Field


class BackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    components: dict = Field(default_factory=dict)
    label: str = Field("", max_length=40)  # same cap as the file name suffix built from it


class RestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    components: dict = Field(default_factory=dict)


class RetentionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Days to keep (1-365), 0 = disabled, negative = number of backups to keep
    # (1-100): the bounds of the settings screen.
    days: int = Field(ge=-100, le=365)


class SetDirectoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str

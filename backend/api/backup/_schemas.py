"""Pydantic models for the backup API."""
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from constants.backup import BACKUP_LABEL_MAX_LENGTH
from services.backup import ComponentName


class BackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    components: dict[ComponentName, StrictBool] = Field(default_factory=dict)
    label: str = Field("", max_length=BACKUP_LABEL_MAX_LENGTH)  # the file name suffix built from it


class RestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    components: dict[ComponentName, StrictBool] = Field(default_factory=dict)


class RetentionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Days to keep (1-365), 0 = disabled, negative = number of backups to keep
    # (1-100): the bounds of the settings screen. Strict: true or "30" is refused.
    days: int = Field(ge=-100, le=365, strict=True)


class SetDirectoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str

"""Request bodies of the portal chat routes, and the check that keeps text the
database cannot store out of both send paths (HTTP and WebSocket)."""
from pydantic import BaseModel, ConfigDict, Field, field_validator


def is_storable(text: str) -> bool:
    """False for text the database cannot store: a NUL or a lone surrogate."""
    if "\x00" in text:
        return False
    try:
        text.encode()
    except UnicodeEncodeError:
        return False
    return True


class SendMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(..., min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def _content_storable(cls, value: str) -> str:
        if not is_storable(value):
            raise ValueError("unstorable_content")
        return value


class MarkRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Newest message the panel displayed: later ones stay unread.
    up_to: int | None = Field(None, ge=1)


class ReportMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = Field(None, max_length=500)

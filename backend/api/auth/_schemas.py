"""Pydantic schemas for the authentication endpoints."""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.security import MAX_BCRYPT_PASSWORD_BYTES, password_byte_length


class LoginRequest(BaseModel):
    """Rejects unknown keys so a hostile client can't probe for hidden
    fields and a buggy client that mistypes a key (e.g. ``passwd``
    instead of ``password``) fails loudly with 422 instead of being
    silently authenticated against the wrong field."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=500)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password:     str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 12:
            raise ValueError("Le mot de passe doit contenir au moins 12 caracteres")
        if password_byte_length(v) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError(
                f"Le mot de passe ne doit pas depasser {MAX_BCRYPT_PASSWORD_BYTES} octets UTF-8"
            )
        if not re.search(r'[A-Z]', v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r'[0-9]', v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError("Le mot de passe doit contenir au moins un caractere special")
        if len(set(v)) < 12:
            raise ValueError("Le mot de passe doit contenir au moins 12 caracteres differents")
        return v


class PreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme:             str = "dark"  # dark|light|amoled|slate|nord|mocha|aurora|cinema|cassette|obsidian|sakura
    sidebar_collapsed: bool = False
    accent:            str = "indigo"
    locale:            str = "fr"
    radius:            int = 12
    particles:         bool = True
    glow:              float = 1.0


class LocaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: str = Field(..., min_length=2, max_length=8)

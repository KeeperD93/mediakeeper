from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by all models (SQLAlchemy 2.x)."""
    pass

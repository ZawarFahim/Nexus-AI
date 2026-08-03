import uuid
from typing import Any
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

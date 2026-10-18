import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    # A length floor only -- not a full password-strength policy (zxcvbn-style
    # strength scoring is a reasonable future enhancement, not required for
    # a dev/test-only checkpoint). 8 is a low bar; raise before public launch.
    password: str = Field(min_length=8, max_length=256)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_active: bool
    email_verified_at: datetime | None
    created_at: datetime

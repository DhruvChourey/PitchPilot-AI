import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from app.models.lead import LeadStatus


class LeadBase(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    website: HttpUrl | None = None
    industry: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: EmailStr | None = None
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("company_name")
    @classmethod
    def company_name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("company_name must not be blank")
        return stripped


class LeadCreate(LeadBase):
    status: LeadStatus = LeadStatus.NEW


class LeadUpdate(BaseModel):
    # company_name and status back NOT NULL columns. Omitting a field from
    # the PATCH body leaves it untouched (handled via exclude_unset at the
    # call site); explicitly sending `null` for either is rejected below
    # rather than allowed through to a database NOT NULL violation.
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    website: HttpUrl | None = None
    industry: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: EmailStr | None = None
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)
    status: LeadStatus | None = None

    @field_validator("company_name")
    @classmethod
    def company_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("company_name cannot be set to null")
        stripped = value.strip()
        if not stripped:
            raise ValueError("company_name must not be blank")
        return stripped

    @field_validator("status")
    @classmethod
    def status_must_not_be_null(cls, value: LeadStatus | None) -> LeadStatus | None:
        if value is None:
            raise ValueError("status cannot be set to null")
        return value


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    website: str | None
    industry: str | None
    contact_name: str | None
    contact_email: str | None
    source: str | None
    notes: str | None
    status: LeadStatus
    created_at: datetime
    updated_at: datetime


class LeadList(BaseModel):
    items: list[LeadRead]
    total: int
    page: int
    page_size: int

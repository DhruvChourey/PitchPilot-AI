import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import LeadCreate, LeadList, LeadRead, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])

MAX_PAGE_SIZE = 100


def _get_lead_or_404(db: Session, lead_id: uuid.UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.post("", response_model=LeadRead, status_code=http_status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    lead = Lead(
        company_name=payload.company_name,
        website=str(payload.website) if payload.website else None,
        industry=payload.industry,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        source=payload.source,
        notes=payload.notes,
        status=payload.status,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("", response_model=LeadList)
def list_leads(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
    lead_status: LeadStatus | None = Query(default=None, alias="status"),
) -> LeadList:
    stmt = select(Lead)
    count_stmt = select(func.count()).select_from(Lead)

    if lead_status is not None:
        stmt = stmt.where(Lead.status == lead_status)
        count_stmt = count_stmt.where(Lead.status == lead_status)

    total = db.scalar(count_stmt) or 0

    stmt = stmt.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt))

    return LeadList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)) -> Lead:
    return _get_lead_or_404(db, lead_id)


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(lead_id: uuid.UUID, payload: LeadUpdate, db: Session = Depends(get_db)) -> Lead:
    lead = _get_lead_or_404(db, lead_id)

    updates = payload.model_dump(exclude_unset=True)
    if "website" in updates:
        updates["website"] = str(updates["website"]) if updates["website"] else None

    for field, value in updates.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", response_model=LeadRead)
def archive_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)) -> Lead:
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.ARCHIVED
    db.commit()
    db.refresh(lead)
    return lead

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadList, LeadRead, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])

MAX_PAGE_SIZE = 100


def _get_owned_lead_or_404(db: Session, lead_id: uuid.UUID, owner_id: uuid.UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    # Identical 404 whether the lead doesn't exist at all or belongs to
    # someone else -- never reveal that another user's lead exists.
    if lead is None or lead.owner_id != owner_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.post("", response_model=LeadRead, status_code=http_status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Lead:
    lead = Lead(
        owner_id=current_user.id,
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
    # No db.refresh() after commit: created_at/updated_at (server_default
    # func.now()) are populated by SQLAlchemy's automatic RETURNING-based
    # "eager defaults" during the flush that commit() performs -- i.e.
    # while this transaction (and the RLS GUC it holds) is still active,
    # not in a new transaction afterward. See DECISIONS.md for why a
    # refresh() here used to break under the restricted, RLS-enforcing
    # runtime role.
    db.commit()
    return lead


@router.get("", response_model=LeadList)
def list_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
    lead_status: LeadStatus | None = Query(default=None, alias="status"),
) -> LeadList:
    stmt = select(Lead).where(Lead.owner_id == current_user.id)
    count_stmt = select(func.count()).select_from(Lead).where(Lead.owner_id == current_user.id)

    if lead_status is not None:
        stmt = stmt.where(Lead.status == lead_status)
        count_stmt = count_stmt.where(Lead.status == lead_status)

    total = db.scalar(count_stmt) or 0

    stmt = stmt.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt))

    return LeadList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Lead:
    return _get_owned_lead_or_404(db, lead_id, current_user.id)


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Lead:
    lead = _get_owned_lead_or_404(db, lead_id, current_user.id)

    updates = payload.model_dump(exclude_unset=True)
    if "website" in updates:
        updates["website"] = str(updates["website"]) if updates["website"] else None

    for field, value in updates.items():
        setattr(lead, field, value)

    # No db.refresh() after commit -- see create_lead's comment above;
    # updated_at (onupdate=func.now()) is likewise populated via RETURNING
    # during this same commit's flush, before the transaction ends.
    db.commit()
    return lead


@router.delete("/{lead_id}", response_model=LeadRead)
def archive_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Lead:
    lead = _get_owned_lead_or_404(db, lead_id, current_user.id)
    lead.status = LeadStatus.ARCHIVED
    # No db.refresh() after commit -- same reasoning as create_lead/update_lead.
    db.commit()
    return lead

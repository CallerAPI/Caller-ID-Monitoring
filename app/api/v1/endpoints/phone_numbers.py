from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, List
from app.api.deps import (
    LookupServiceFactory,
    get_current_user,
    get_db,
    get_lookup_service_factory,
    require_api_key,
)
from app.models.phone_number import (
    PhoneNumber,
    PhoneNumberCreate,
    PhoneNumberUpdate,
    PhoneNumberSchema
)
from app.models.user import User
from app.services.monitor import add_job_for_number, remove_job_for_number

router = APIRouter()


def get_owned_phone_number(db: Session, owner: User, phone_number_id: int) -> PhoneNumber:
    db_phone_number = db.query(PhoneNumber).filter(
        PhoneNumber.id == phone_number_id,
        PhoneNumber.owner_id == owner.id,
    ).first()
    if not db_phone_number:
        raise HTTPException(status_code=404, detail="Phone number not found")
    return db_phone_number


def ensure_number_not_monitored(db: Session, owner: User, number: str, exclude_id: int | None = None):
    query = db.query(PhoneNumber).filter(
        PhoneNumber.owner_id == owner.id,
        PhoneNumber.number == number,
    )
    if exclude_id is not None:
        query = query.filter(PhoneNumber.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=400,
            detail=f"Phone number {number} is already being monitored"
        )


def lookup_details(service_factory: LookupServiceFactory, api_key: str, number: str) -> Dict[str, Any]:
    lookup_data = service_factory(api_key).lookup_number(number)
    if not lookup_data or "data" not in lookup_data:
        raise ValueError("Invalid response from CallerAPI")

    data = lookup_data["data"]
    business_info = data.get("business_info", {}) or {}

    location_parts = [
        business_info[part] for part in ("city", "state", "country") if business_info.get(part)
    ]

    return {
        "entity_type": data.get("entity_type", "UNKNOWN"),
        "business_name": business_info.get("business_name"),
        "business_category": business_info.get("category"),
        "business_industry": business_info.get("industry"),
        "business_location": ", ".join(location_parts) if location_parts else None,
        "is_spam": data.get("is_spam", False),
        "spam_reports": data.get("total_complaints", 0),
        "complaints": data.get("complaints"),
    }


@router.get("/", response_model=List[PhoneNumberSchema])
def read_phone_numbers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the phone numbers of the current user.
    """
    return db.query(PhoneNumber).filter(PhoneNumber.owner_id == current_user.id).all()


@router.get("/{phone_number_id}", response_model=PhoneNumberSchema)
def read_phone_number(
    phone_number_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve one phone number of the current user.
    """
    return get_owned_phone_number(db, current_user, phone_number_id)


@router.post("/", response_model=PhoneNumberSchema)
def create_phone_number(
    phone_number: PhoneNumberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service_factory: LookupServiceFactory = Depends(get_lookup_service_factory),
):
    """
    Create a new phone number to monitor.
    """
    api_key = require_api_key(current_user)
    ensure_number_not_monitored(db, current_user, phone_number.number)

    try:
        details = lookup_details(service_factory, api_key, phone_number.number)

        db_phone_number = PhoneNumber(
            owner_id=current_user.id,
            number=phone_number.number,
            monitoring_frequency=phone_number.monitoring_frequency,
            disabled=False,
            **details,
        )
        db.add(db_phone_number)
        db.commit()
        db.refresh(db_phone_number)

        add_job_for_number(db_phone_number.id, db_phone_number.monitoring_frequency)

        return db_phone_number
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{phone_number_id}", response_model=PhoneNumberSchema)
def update_phone_number(
    phone_number_id: int,
    phone_number: PhoneNumberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service_factory: LookupServiceFactory = Depends(get_lookup_service_factory),
):
    """
    Update a phone number's details.
    """
    db_phone_number = get_owned_phone_number(db, current_user, phone_number_id)

    update_data = phone_number.dict(exclude_unset=True)

    if 'number' in update_data:
        api_key = require_api_key(current_user)
        ensure_number_not_monitored(db, current_user, update_data['number'], exclude_id=phone_number_id)

        try:
            details = lookup_details(service_factory, api_key, update_data['number'])
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        db_phone_number.number = update_data['number']
        for field, value in details.items():
            setattr(db_phone_number, field, value)

    if 'monitoring_frequency' in update_data:
        if update_data['monitoring_frequency'] < 1 or update_data['monitoring_frequency'] > 1440:
            raise HTTPException(status_code=400, detail="Monitoring frequency must be between 1 and 1440 minutes")
        db_phone_number.monitoring_frequency = update_data['monitoring_frequency']

    if 'disabled' in update_data:
        db_phone_number.disabled = update_data['disabled']

    db.commit()
    db.refresh(db_phone_number)

    if db_phone_number.disabled:
        remove_job_for_number(phone_number_id)
    elif 'disabled' in update_data or 'monitoring_frequency' in update_data:
        add_job_for_number(phone_number_id, db_phone_number.monitoring_frequency)

    return db_phone_number


@router.delete("/{phone_number_id}")
def delete_phone_number(
    phone_number_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a phone number.
    """
    db_phone_number = get_owned_phone_number(db, current_user, phone_number_id)

    remove_job_for_number(phone_number_id)

    db.delete(db_phone_number)
    db.commit()
    return {"ok": True}

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.base import SessionLocal
from app.models.phone_number import (
    PhoneNumber,
    PhoneNumberCreate,
    PhoneNumberUpdate,
    PhoneNumberSchema
)
from app.services.caller_api import CallerAPIService
from app.services.monitor import add_job_for_number, remove_job_for_number

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get API key from session
def get_api_key(request: Request):
    api_key = request.session.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return api_key

@router.get("/", response_model=List[PhoneNumberSchema])
def read_phone_numbers(request: Request, db: Session = Depends(get_db)):
    """
    Retrieve all phone numbers.
    """
    if not request.session.get("api_key"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return db.query(PhoneNumber).all()

@router.post("/", response_model=PhoneNumberSchema)
def create_phone_number(
    request: Request,
    phone_number: PhoneNumberCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new phone number to monitor.
    """
    api_key = request.session.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Check if phone number already exists
    existing_number = db.query(PhoneNumber).filter(PhoneNumber.number == phone_number.number).first()
    if existing_number:
        raise HTTPException(
            status_code=400,
            detail=f"Phone number {phone_number.number} is already being monitored"
        )

    service = CallerAPIService(api_key=api_key)
    try:
        lookup_data = service.lookup_number(phone_number.number)
        if not lookup_data or "data" not in lookup_data:
            raise ValueError("Invalid response from CallerAPI")
            
        data = lookup_data["data"]
        business_info = data.get("business_info", {}) or {}
        
        # Build location string from business info
        location_parts = []
        if business_info.get("city"):
            location_parts.append(business_info["city"])
        if business_info.get("state"):
            location_parts.append(business_info["state"])
        if business_info.get("country"):
            location_parts.append(business_info["country"])
        business_location = ", ".join(location_parts) if location_parts else None
        
        # Create new phone number in DB
        db_phone_number = PhoneNumber(
            number=phone_number.number,
            monitoring_frequency=phone_number.monitoring_frequency,
            entity_type=data.get("entity_type", "UNKNOWN"),
            business_name=business_info.get("business_name"),
            business_category=business_info.get("category"),
            business_industry=business_info.get("industry"),
            business_location=business_location,
            is_spam=data.get("is_spam", False),
            spam_reports=data.get("total_complaints", 0),
            complaints=data.get("complaints"),
            disabled=False
        )
        db.add(db_phone_number)
        db.commit()
        db.refresh(db_phone_number)
        
        # Start monitoring this number
        add_job_for_number(db_phone_number.id, db_phone_number.monitoring_frequency, api_key)
        
        return db_phone_number
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{phone_number_id}", response_model=PhoneNumberSchema)
def update_phone_number(
    request: Request,
    phone_number_id: int,
    phone_number: PhoneNumberUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a phone number's details.
    """
    api_key = request.session.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    db_phone_number = db.query(PhoneNumber).filter(PhoneNumber.id == phone_number_id).first()
    if not db_phone_number:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    update_data = phone_number.dict(exclude_unset=True)
    
    # Handle phone number update
    if 'number' in update_data:
        # Check if new number already exists
        existing_number = db.query(PhoneNumber).filter(
            PhoneNumber.number == update_data['number'],
            PhoneNumber.id != phone_number_id
        ).first()
        if existing_number:
            raise HTTPException(
                status_code=400,
                detail=f"Phone number {update_data['number']} is already being monitored"
            )
            
        # Lookup new number in CallerAPI
        service = CallerAPIService(api_key=api_key)
        try:
            lookup_data = service.lookup_number(update_data['number'])
            if not lookup_data or "data" not in lookup_data:
                raise ValueError("Invalid response from CallerAPI")
                
            data = lookup_data["data"]
            business_info = data.get("business_info", {}) or {}
            
            # Build location string from business info
            location_parts = []
            if business_info.get("city"):
                location_parts.append(business_info["city"])
            if business_info.get("state"):
                location_parts.append(business_info["state"])
            if business_info.get("country"):
                location_parts.append(business_info["country"])
            business_location = ", ".join(location_parts) if location_parts else None
            
            # Update number and its metadata
            db_phone_number.number = update_data['number']
            db_phone_number.entity_type = data.get("entity_type", "UNKNOWN")
            db_phone_number.business_name = business_info.get("business_name")
            db_phone_number.business_category = business_info.get("category")
            db_phone_number.business_industry = business_info.get("industry")
            db_phone_number.business_location = business_location
            db_phone_number.is_spam = data.get("is_spam", False)
            db_phone_number.spam_reports = data.get("total_complaints", 0)
            db_phone_number.complaints = data.get("complaints")
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Handle disabled status
    if 'disabled' in update_data:
        db_phone_number.disabled = update_data['disabled']
        if update_data['disabled']:
            remove_job_for_number(phone_number_id)
        else:
            add_job_for_number(phone_number_id, db_phone_number.monitoring_frequency, api_key)
    
    # Handle monitoring frequency
    if 'monitoring_frequency' in update_data:
        if update_data['monitoring_frequency'] < 1 or update_data['monitoring_frequency'] > 1440:
            raise HTTPException(status_code=400, detail="Monitoring frequency must be between 1 and 1440 minutes")
        db_phone_number.monitoring_frequency = update_data['monitoring_frequency']
        if not db_phone_number.disabled:
            add_job_for_number(phone_number_id, update_data['monitoring_frequency'], api_key)
    
    db.commit()
    db.refresh(db_phone_number)
    return db_phone_number

@router.delete("/{phone_number_id}")
def delete_phone_number(request: Request, phone_number_id: int, db: Session = Depends(get_db)):
    """
    Delete a phone number.
    """
    if not request.session.get("api_key"):
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    db_phone_number = db.query(PhoneNumber).filter(PhoneNumber.id == phone_number_id).first()
    if not db_phone_number:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    # Stop monitoring this number
    remove_job_for_number(phone_number_id)
    
    db.delete(db_phone_number)
    db.commit()
    return {"ok": True} 
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Location
from ..schemas import LocationCreate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[Location])
def list_locations(session: Session = Depends(get_session)):
    return session.exec(select(Location).order_by(Location.name)).all()


@router.post("", response_model=Location, status_code=201)
def create_location(payload: LocationCreate, session: Session = Depends(get_session)):
    exists = session.exec(
        select(Location).where(Location.name == payload.name)
    ).first()
    if exists:
        return exists
    loc = Location(**payload.model_dump())
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc


@router.get("/{location_id}", response_model=Location)
def get_location(location_id: int, session: Session = Depends(get_session)):
    loc = session.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="ไม่พบพื้นที่เก็บ")
    return loc

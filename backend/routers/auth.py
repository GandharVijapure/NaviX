"""
Auth endpoints: registration + login for volunteers and control-room/admin
staff. Pilgrims never hit this router -- their features stay anonymous.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User, UserRole, Volunteer

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=schemas.TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Volunteers automatically get a linked Volunteer row so they show up on
    # the control-room map / nearby-volunteer lookups right after signing up.
    if user.role == UserRole.volunteer:
        volunteer = Volunteer(
            user_id=user.id,
            name=user.name,
            phone=user.phone,
            device_id=payload.device_id,
            latitude=payload.latitude if payload.latitude is not None else 18.5204,
            longitude=payload.longitude if payload.longitude is not None else 73.8567,
            assigned_zone=payload.assigned_zone,
        )
        db.add(volunteer)
        db.commit()

    token = create_access_token(user)
    return schemas.TokenOut(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token(user)
    return schemas.TokenOut(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

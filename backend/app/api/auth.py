"""
MedAssist AI - Authentication API
Handles user registration, login, and token management
"""

from fastapi import APIRouter, HTTPException, status, Depends
import logging

from app.models.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.database.connection import get_db
from app.utils.audit_logger import log_action

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new staff/admin user"""
    db = get_db()

    # Check if email already exists
    existing = await db.user.find_unique(where={"email": request.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = await db.user.create(
        data={
            "email": request.email,
            "passwordHash": hash_password(request.password),
            "name": request.name,
            "phone": request.phone,
            "role": request.role.value,
        }
    )

    await log_action("USER_REGISTER", "users", user.id)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=request.role,
        phone=user.phone,
        is_active=user.isActive,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate and receive JWT token"""
    db = get_db()

    user = await db.user.find_unique(where={"email": request.email})
    if not user or not verify_password(request.password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.isActive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Create JWT token
    token = create_access_token(data={
        "sub": user.id,
        "email": user.email,
        "role": user.role,
    })

    await log_action("USER_LOGIN", "users", user.id)

    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user profile"""
    db = get_db()

    user = await db.user.find_unique(where={"id": current_user["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        phone=user.phone,
        is_active=user.isActive,
    )

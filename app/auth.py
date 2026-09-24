"""
Authentication router for Support CRM Backend.

This module provides JWT-based authentication endpoints including user registration,
login, and profile retrieval. It handles password hashing, token generation,
and user validation.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import database, models, schemas
from app.routers.utils import (
    authenticate_user,
    authenticate_customer,
    create_access_token,
    get_current_active_user,
    get_current_customer,
    get_password_hash
)

# Create the authentication router
router = APIRouter()

@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Register a new user account.

    Checks for existing username and email, hashes the password,
    creates the user in the database, and returns the user data.

    Args:
        user: User creation data (username, email, password, role)
        db: Database session dependency

    Returns:
        UserOut: Created user data

    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username already exists
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password and create user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )

    # Save to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Authenticate user and return JWT access token.

    Validates username/password combination and generates a JWT token
    with 30-minute expiration.

    Args:
        form_data: OAuth2 form data with username and password
        db: Database session dependency

    Returns:
        Token: JWT access token and type

    Raises:
        HTTPException: If authentication fails
    """
    # Authenticate user credentials
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """
    Get current authenticated user's profile information.

    Requires valid JWT token in Authorization header.

    Args:
        current_user: Current authenticated user (injected by dependency)

    Returns:
        UserOut: Current user's profile data
    """
    return current_user

# ===== CUSTOMER AUTHENTICATION ENDPOINTS =====

@router.post("/customer/register", response_model=schemas.CustomerOut)
def register_customer(customer_in: schemas.CustomerRegister, db: Session = Depends(database.get_db)):
    """
    Register a new customer account.

    Checks if email already exists, hashes password, saves the customer,
    and returns the created customer profile.

    Args:
        customer_in: Customer registration data (name, email, password, phone, company, notes)
        db: Database session dependency

    Returns:
        CustomerOut: Created customer data

    Raises:
        HTTPException: If email is already registered
    """
    # Check if email is already taken
    existing_customer = db.query(models.Customer).filter(models.Customer.email == customer_in.email).first()
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password securely
    hashed_password = get_password_hash(customer_in.password)

    db_customer = models.Customer(
        name=customer_in.name,
        email=customer_in.email,
        phone=customer_in.phone,
        company=customer_in.company,
        notes=customer_in.notes,
        hashed_password=hashed_password
    )

    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

@router.post("/customer/login")
def login_customer(credentials: schemas.CustomerLogin, db: Session = Depends(database.get_db)):
    """
    Authenticate customer with email and password and return JWT access token.

    Args:
        credentials: Customer login data (email and password)
        db: Database session dependency

    Returns:
        dict: Access token, token type, and customer info

    Raises:
        HTTPException: If credentials are invalid
    """
    customer = authenticate_customer(db, credentials.email, credentials.password)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={
            "sub": customer.email,
            "role": "customer",
            "customer_id": customer.id,
            "name": customer.name
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "customer",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "company": customer.company
        }
    }

@router.get("/customer/me", response_model=schemas.CustomerOut)
def read_customers_me(current_customer: models.Customer = Depends(get_current_customer)):
    """
    Get the currently authenticated customer's profile information.

    Requires valid customer JWT token in Authorization header.

    Args:
        current_customer: Current authenticated customer dependency

    Returns:
        CustomerOut: Current customer's profile data
    """
    return current_customer

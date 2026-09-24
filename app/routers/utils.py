"""
Authentication utilities for Support CRM Backend.

This module provides essential authentication functions including password hashing,
JWT token creation and validation, user authentication, and dependency injection
for securing API endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app import models, database

# JWT Configuration
# TODO: Move SECRET_KEY to environment variables for production security
SECRET_KEY = "your-secret-key"  # Change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hashed version.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against

    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with optional expiration.

    Args:
        data: Dictionary containing token payload data (e.g., {"sub": username})
        expires_delta: Optional timedelta for token expiration

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default to 15 minutes if no expiration provided
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})

    # Encode and return JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Authenticate a user by username and password.

    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password

    Returns:
        User object if authentication successful, False otherwise
    """
    # Find user by username
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return False

    # Verify password
    if not verify_password(password, user.hashed_password):
        return False

    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.User:
    """
    Dependency function to get the current authenticated user from JWT token.

    Args:
        token: JWT access token from Authorization header
        db: Database session dependency

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Find user in database
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception

    return user

def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency function to get the current active user.

    Extends get_current_user to also check if the user account is active.

    Args:
        current_user: User object from get_current_user dependency

    Returns:
        User: The active authenticated user

    Raises:
        HTTPException: If user account is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def authenticate_customer(db: Session, email: str, password: str):
    """
    Authenticate a customer by email and password.

    Args:
        db: Database session
        email: Customer email address
        password: Plain text password

    Returns:
        Customer object if authentication successful, False otherwise
    """
    customer = db.query(models.Customer).filter(models.Customer.email == email).first()
    if not customer:
        return False

    if not customer.hashed_password:
        return False

    if not verify_password(password, customer.hashed_password):
        return False

    return customer

def get_current_customer(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.Customer:
    """
    Dependency function to get the current authenticated customer from JWT token.

    Args:
        token: JWT access token from Authorization header
        db: Database session dependency

    Returns:
        Customer: The authenticated customer object

    Raises:
        HTTPException: If token is invalid or customer not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate customer credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        customer_id: Optional[int] = payload.get("customer_id")
        if email is None and customer_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    customer = None
    if customer_id:
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer and email:
        customer = db.query(models.Customer).filter(models.Customer.email == email).first()

    if customer is None:
        raise credentials_exception

    return customer

class CurrentActor:
    """
    Represents the authenticated actor: either a staff User or a Customer.
    Used for endpoints accessible by both staff and customers (e.g., tickets).
    """
    def __init__(self, actor_type: str, user: Optional[models.User] = None, customer: Optional[models.Customer] = None):
        self.actor_type = actor_type  # 'user' or 'customer'
        self.user = user
        self.customer = customer

    @property
    def is_customer(self) -> bool:
        return self.actor_type == "customer"

    @property
    def is_agent(self) -> bool:
        return self.actor_type == "user" and self.user is not None and self.user.role in ("agent", "admin")

    @property
    def is_admin(self) -> bool:
        return self.actor_type == "user" and self.user is not None and self.user.role == "admin"

def get_current_actor(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> CurrentActor:
    """
    Dependency function to authenticate either a staff User or a Customer.
    Allows endpoints to handle both types of users with appropriate role checks.

    Args:
        token: JWT access token from Authorization header
        db: Database session dependency

    Returns:
        CurrentActor: An object representing the authenticated user or customer

    Raises:
        HTTPException: If token is invalid or account not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        role: str = payload.get("role")
        customer_id: Optional[int] = payload.get("customer_id")
        if sub is None and customer_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Explicit customer role or token with customer_id
    if role == "customer" or customer_id is not None:
        customer = None
        if customer_id:
            customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
        if not customer and sub:
            customer = db.query(models.Customer).filter(models.Customer.email == sub).first()
        if customer:
            return CurrentActor(actor_type="customer", customer=customer)

    # Check staff user by username
    if sub:
        user = db.query(models.User).filter(models.User.username == sub).first()
        if user:
            if not user.is_active:
                raise HTTPException(status_code=400, detail="Inactive user")
            return CurrentActor(actor_type="user", user=user)

    # Fallback to customer by email
    if sub:
        customer = db.query(models.Customer).filter(models.Customer.email == sub).first()
        if customer:
            return CurrentActor(actor_type="customer", customer=customer)

    raise credentials_exception

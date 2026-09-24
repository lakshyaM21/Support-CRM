"""
Customer router for Support CRM Backend.

This module provides CRUD endpoints for managing customer profiles,
including creation, retrieval, update, and deletion of customer data.
Supports staff management and customer self-profile retrieval with proper authorization.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, database
from app.routers.utils import get_current_active_user, get_current_actor, CurrentActor

# Create the customer router
router = APIRouter()

@router.post("/", response_model=schemas.CustomerOut)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Create a new customer profile.
    Requires staff authentication.

    Args:
        customer: Customer creation data
        db: Database session dependency
        current_user: Current authenticated user dependency

    Returns:
        CustomerOut: Created customer data

    Raises:
        HTTPException: If customer with this email already exists
    """
    existing = db.query(models.Customer).filter(models.Customer.email == customer.email).first()
    if existing:
        return existing

    customer_dict = customer.model_dump() if hasattr(customer, "model_dump") else customer.dict()
    new_customer = models.Customer(**customer_dict)
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@router.get("/", response_model=List[schemas.CustomerOut])
def get_customers(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Retrieve a list of all customers.
    Requires staff authentication.

    Args:
        db: Database session dependency
        current_user: Current authenticated user dependency

    Returns:
        List[CustomerOut]: List of customer profiles
    """
    return db.query(models.Customer).all()

@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(database.get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Retrieve a specific customer by ID.

    Customers are authorized to view ONLY their own profile.
    Staff members can view any customer.

    Args:
        customer_id: ID of the customer to retrieve
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        CustomerOut: Customer profile data

    Raises:
        HTTPException: 404 if not found, 403 if unauthorized customer
    """
    if current_actor.is_customer and current_actor.customer.id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this customer profile"
        )

    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(
    customer_id: int,
    customer_update: schemas.CustomerUpdate,
    db: Session = Depends(database.get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Update an existing customer profile.

    Customers can update their own profile.
    Staff members can update any customer profile.

    Args:
        customer_id: ID of the customer to update
        customer_update: Updated customer data
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        CustomerOut: Updated customer data

    Raises:
        HTTPException: 404 if not found, 403 if unauthorized customer
    """
    if current_actor.is_customer and current_actor.customer.id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this customer profile"
        )

    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer_update.model_dump(exclude_unset=True) if hasattr(customer_update, "model_dump") else customer_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer

@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Delete a customer profile.
    Requires staff authentication.

    Args:
        customer_id: ID of the customer to delete
        db: Database session dependency
        current_user: Current authenticated user dependency

    Returns:
        dict: Success message

    Raises:
        HTTPException: If customer not found
    """
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted successfully"}

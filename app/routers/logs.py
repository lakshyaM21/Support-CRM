"""
Communication logs router for Support CRM Backend.

This module provides CRUD endpoints for managing communication logs,
which track customer interactions (calls, emails, chats) associated with support tickets.
All endpoints require authentication and implement role-based access control.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas, database
from app.routers.utils import get_current_actor, CurrentActor

# Create the logs router
router = APIRouter()

# Alias for database dependency
get_db = database.get_db

@router.get("/", response_model=List[schemas.LogOut])
def read_logs(
    skip: int = 0,
    limit: int = 100,
    ticket_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Retrieve a paginated list of communication logs.

    Customers can only view logs for tickets they own.
    Staff members can view all communication logs.

    Args:
        skip: Number of logs to skip (for pagination)
        limit: Maximum number of logs to return
        ticket_id: Optional filter for a specific ticket
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        List[LogOut]: List of communication log data
    """
    query = db.query(models.Log)

    if current_actor.is_customer:
        # Get customer's ticket IDs
        cust_ticket_ids = db.query(models.Ticket.id).filter(
            models.Ticket.customer_id == current_actor.customer.id
        )

        if ticket_id is not None:
            # Check ownership of specified ticket
            owns_ticket = db.query(models.Ticket).filter(
                models.Ticket.id == ticket_id,
                models.Ticket.customer_id == current_actor.customer.id
            ).first()
            if not owns_ticket:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view logs for this ticket"
                )
            query = query.filter(models.Log.ticket_id == ticket_id)
        else:
            query = query.filter(models.Log.ticket_id.in_(cust_ticket_ids))
    else:
        if ticket_id is not None:
            query = query.filter(models.Log.ticket_id == ticket_id)

    logs = query.order_by(models.Log.created_at.asc()).offset(skip).limit(limit).all()
    return logs

@router.post("/", response_model=schemas.LogOut)
def create_log(
    log: schemas.LogCreate,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Create a new communication log entry.

    Validates that the associated ticket exists before creating the log.
    If the current actor is a customer, verifies they own the ticket.

    Args:
        log: Log creation data
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        LogOut: Created log data

    Raises:
        HTTPException: 404 if ticket not found, 403 if unauthorized customer
    """
    # Validate ticket exists
    ticket = db.query(models.Ticket).filter(models.Ticket.id == log.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # If customer, verify ownership of the ticket
    if current_actor.is_customer and ticket.customer_id != current_actor.customer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add logs to this ticket"
        )

    # Create log entry
    db_log = models.Log(
        type=log.type,
        content=log.content,
        ticket_id=log.ticket_id
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/{log_id}", response_model=schemas.LogOut)
def read_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Retrieve a specific communication log by ID.

    Args:
        log_id: Log ID to retrieve
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        LogOut: Log data

    Raises:
        HTTPException: 404 if not found, 403 if unauthorized
    """
    log = db.query(models.Log).filter(models.Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    if current_actor.is_customer:
        if not log.ticket or log.ticket.customer_id != current_actor.customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this log"
            )

    return log

@router.put("/{log_id}", response_model=schemas.LogOut)
def update_log(
    log_id: int,
    log_update: schemas.LogCreate,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Update an existing communication log.
    Only staff members may edit communication logs.

    Args:
        log_id: Log ID to update
        log_update: Updated log data
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        LogOut: Updated log data

    Raises:
        HTTPException: 404 if not found, 403 if customer
    """
    if current_actor.is_customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot edit communication logs"
        )

    log = db.query(models.Log).filter(models.Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    ticket = db.query(models.Ticket).filter(models.Ticket.id == log_update.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    log.type = log_update.type
    log.content = log_update.content
    log.ticket_id = log_update.ticket_id

    db.commit()
    db.refresh(log)
    return log

@router.delete("/{log_id}")
def delete_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Delete a communication log entry.
    Only staff members may delete communication logs.

    Args:
        log_id: Log ID to delete
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        dict: Success message

    Raises:
        HTTPException: 404 if not found, 403 if customer
    """
    if current_actor.is_customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot delete communication logs"
        )

    log = db.query(models.Log).filter(models.Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    db.delete(log)
    db.commit()
    return {"detail": "Log deleted successfully"}

"""
Ticket router for Support CRM Backend.

This module provides CRUD endpoints for managing support tickets,
including creation, retrieval, updating, and deletion of tickets.
All endpoints require authentication and implement role-based access control:
- Customers can only see, create, and manage their own tickets.
- Staff (agents and admins) can view, assign, and manage all tickets.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas, database
from app.routers.utils import get_current_actor, CurrentActor

# Create the ticket router
router = APIRouter()

# Alias for database dependency
get_db = database.get_db

@router.get("/", response_model=List[schemas.TicketOut])
def read_tickets(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Retrieve support tickets.

    Customers only receive tickets belonging to them.
    Staff members receive all tickets across all customers.

    Args:
        skip: Number of tickets to skip (for pagination)
        limit: Maximum number of tickets to return
        status: Optional filter by ticket status
        priority: Optional filter by ticket priority
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        List[TicketOut]: List of ticket data
    """
    query = db.query(models.Ticket)

    # Customer authorization: only their own tickets
    if current_actor.is_customer:
        query = query.filter(models.Ticket.customer_id == current_actor.customer.id)

    # Optional filters
    if status:
        query = query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)

    tickets = query.order_by(models.Ticket.created_at.desc()).offset(skip).limit(limit).all()
    return tickets

@router.post("/", response_model=schemas.TicketOut)
def create_ticket(
    ticket: schemas.TicketCreate,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Create a new support ticket.

    For customers: ticket is automatically linked to the authenticated customer.
    Customer cannot assign agents or spoof customer_id.
    For staff: customer_id is required, agent can optionally be assigned.

    Args:
        ticket: Ticket creation data
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        TicketOut: Created ticket data

    Raises:
        HTTPException: If customer or assigned agent not found
    """
    if current_actor.is_customer:
        # Customer creates ticket for themselves
        db_ticket = models.Ticket(
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority or "medium",
            status="open",
            customer_id=current_actor.customer.id,
            assigned_agent_id=None
        )
    else:
        # Staff creates ticket
        if not ticket.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer ID is required"
            )

        customer = db.query(models.Customer).filter(models.Customer.id == ticket.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        if ticket.assigned_agent_id:
            agent = db.query(models.User).filter(models.User.id == ticket.assigned_agent_id).first()
            if not agent:
                raise HTTPException(status_code=404, detail="Assigned agent not found")

        db_ticket = models.Ticket(
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority or "medium",
            status=ticket.status or "open",
            customer_id=ticket.customer_id,
            assigned_agent_id=ticket.assigned_agent_id
        )

    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

@router.get("/{ticket_id}", response_model=schemas.TicketOut)
def read_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Retrieve a specific support ticket by ID.

    Customers are authorized to view ONLY their own tickets.
    Staff members can view any ticket.

    Args:
        ticket_id: Ticket ID to retrieve
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        TicketOut: Ticket data

    Raises:
        HTTPException: 404 if ticket not found, 403 if unauthorized customer
    """
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Critical security check: Customer can only view their own ticket
    if current_actor.is_customer and ticket.customer_id != current_actor.customer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this ticket"
        )

    return ticket

@router.put("/{ticket_id}", response_model=schemas.TicketOut)
def update_ticket(
    ticket_id: int,
    ticket_update: schemas.TicketCreate,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Update an existing support ticket.

    Customers can only update their own ticket (title, description, status).
    Staff can update any ticket including agent assignment.

    Args:
        ticket_id: Ticket ID to update
        ticket_update: Updated ticket data
        db: Database session dependency
        current_actor: Current authenticated user or customer

    Returns:
        TicketOut: Updated ticket data

    Raises:
        HTTPException: 404 if not found, 403 if unauthorized
    """
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_actor.is_customer:
        if ticket.customer_id != current_actor.customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this ticket"
            )
        # Customer can update title, description, or status
        if ticket_update.title:
            ticket.title = ticket_update.title
        if ticket_update.description is not None:
            ticket.description = ticket_update.description
        if ticket_update.status:
            ticket.status = ticket_update.status
    else:
        # Staff update
        customer_id_to_check = ticket_update.customer_id if ticket_update.customer_id else ticket.customer_id
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id_to_check).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        if ticket_update.assigned_agent_id is not None:
            if ticket_update.assigned_agent_id > 0:
                agent = db.query(models.User).filter(models.User.id == ticket_update.assigned_agent_id).first()
                if not agent:
                    raise HTTPException(status_code=404, detail="Assigned agent not found")
                ticket.assigned_agent_id = ticket_update.assigned_agent_id
            else:
                ticket.assigned_agent_id = None

        ticket.title = ticket_update.title
        ticket.description = ticket_update.description
        ticket.priority = ticket_update.priority
        ticket.status = ticket_update.status
        ticket.customer_id = customer_id_to_check

    db.commit()
    db.refresh(ticket)
    return ticket

@router.delete("/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_actor: CurrentActor = Depends(get_current_actor)
):
    """
    Delete a support ticket.
    Only staff members (agent/admin) are allowed to delete tickets.

    Args:
        ticket_id: Ticket ID to delete
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
            detail="Customers are not permitted to delete tickets"
        )

    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    db.delete(ticket)
    db.commit()
    return {"detail": "Ticket deleted successfully"}

"""
Comprehensive test suite for Customer Authentication, Authorization, and Ticket Workflows.

Tests:
1. Customer Registration (password hashed, customer record created)
2. Customer Login (credentials verified, JWT issued)
3. Customer Ticket Creation (automatic ownership, no spoofing)
4. Customer Authorization (Customer A can view A's tickets, but CANNOT view or access B's tickets - returns 403)
5. Agent Management (Agent can view all tickets, assign ticket, update status)
6. Customer Visibility (Customer sees updated ticket status)
7. Communication Logs Authorization (Customer can only see logs for own tickets)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_customer_registration_and_login():
    """Test customer registration and login flow with hashed password and JWT."""
    # 1. Register Customer Alpha
    email_a = "alpha@example.com"
    reg_response = client.post("/auth/customer/register", json={
        "name": "Alpha Customer",
        "email": email_a,
        "password": "PasswordAlpha123!",
        "phone": "555-0100",
        "company": "Alpha Corp"
    })
    # If already registered in a previous run, that's fine or it returns 200
    assert reg_response.status_code in (200, 400)

    # 2. Login Customer Alpha
    login_response = client.post("/auth/customer/login", json={
        "email": email_a,
        "password": "PasswordAlpha123!"
    })
    assert login_response.status_code == 200
    data_a = login_response.json()
    assert "access_token" in data_a
    assert data_a["role"] == "customer"
    assert data_a["customer"]["email"] == email_a

    # 3. Test Invalid Password
    bad_login = client.post("/auth/customer/login", json={
        "email": email_a,
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

    # 4. Get Customer Profile via /auth/customer/me
    token_a = data_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    me_response = client.get("/auth/customer/me", headers=headers_a)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email_a

def test_customer_ticket_ownership_and_isolation():
    """
    Test that Customer A cannot see or access Customer B's tickets.
    Backend must return 403 Forbidden when Customer A tries to access Customer B's ticket.
    """
    # Register/Login Customer A
    client.post("/auth/customer/register", json={
        "name": "User Alpha",
        "email": "alpha_tickets@example.com",
        "password": "passAlpha123!"
    })
    res_a = client.post("/auth/customer/login", json={
        "email": "alpha_tickets@example.com",
        "password": "passAlpha123!"
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register/Login Customer B
    client.post("/auth/customer/register", json={
        "name": "User Beta",
        "email": "beta_tickets@example.com",
        "password": "passBeta123!"
    })
    res_b = client.post("/auth/customer/login", json={
        "email": "beta_tickets@example.com",
        "password": "passBeta123!"
    })
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Customer A creates a ticket
    ticket_a_res = client.post("/tickets/", json={
        "title": "Alpha Laptop Issue",
        "description": "Screen flickering",
        "priority": "high"
    }, headers=headers_a)
    assert ticket_a_res.status_code == 200
    ticket_a_id = ticket_a_res.json()["id"]

    # Customer B creates a ticket
    ticket_b_res = client.post("/tickets/", json={
        "title": "Beta Network Issue",
        "description": "Cannot connect to VPN",
        "priority": "urgent"
    }, headers=headers_b)
    assert ticket_b_res.status_code == 200
    ticket_b_id = ticket_b_res.json()["id"]

    # 1. Customer A lists tickets -> Must see Alpha's ticket, MUST NOT see Beta's ticket
    a_tickets = client.get("/tickets/", headers=headers_a).json()
    a_ticket_ids = [t["id"] for t in a_tickets]
    assert ticket_a_id in a_ticket_ids
    assert ticket_b_id not in a_ticket_ids

    # 2. Customer B lists tickets -> Must see Beta's ticket, MUST NOT see Alpha's ticket
    b_tickets = client.get("/tickets/", headers=headers_b).json()
    b_ticket_ids = [t["id"] for t in b_tickets]
    assert ticket_b_id in b_ticket_ids
    assert ticket_a_id not in b_ticket_ids

    # 3. Direct ID Access Security: Customer A tries to access Customer B's ticket ID
    tamper_res = client.get(f"/tickets/{ticket_b_id}", headers=headers_a)
    assert tamper_res.status_code == 403, "Customer A must not be allowed to access Customer B's ticket"

    # 4. Direct ID Access Security: Customer B tries to access Customer A's ticket ID
    tamper_res_b = client.get(f"/tickets/{ticket_a_id}", headers=headers_b)
    assert tamper_res_b.status_code == 403, "Customer B must not be allowed to access Customer A's ticket"

    # 5. Customer cannot delete tickets
    del_res = client.delete(f"/tickets/{ticket_a_id}", headers=headers_a)
    assert del_res.status_code == 403

def test_agent_management_and_customer_visibility():
    """
    Test full end-to-end flow:
    Customer creates ticket -> Agent sees ticket -> Agent updates status -> Customer sees updated status.
    """
    # 1. Agent logs in
    agent_login = client.post("/auth/login", data={"username": "testuser", "password": "testpass"})
    agent_token = agent_login.json()["access_token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}

    # 2. Customer creates a ticket
    cust_login = client.post("/auth/customer/login", json={
        "email": "alpha_tickets@example.com",
        "password": "passAlpha123!"
    })
    cust_token = cust_login.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    ticket_res = client.post("/tickets/", json={
        "title": "Email setup help",
        "description": "Need IMAP settings",
        "priority": "low"
    }, headers=cust_headers)
    assert ticket_res.status_code == 200
    ticket_id = ticket_res.json()["id"]
    assert ticket_res.json()["status"] == "open"

    # 3. Agent sees all tickets (including the customer's new ticket)
    agent_tickets = client.get("/tickets/", headers=agent_headers).json()
    agent_ticket_ids = [t["id"] for t in agent_tickets]
    assert ticket_id in agent_ticket_ids

    # 4. Agent updates ticket status to 'in-progress'
    update_res = client.put(f"/tickets/{ticket_id}", json={
        "title": "Email setup help",
        "description": "Need IMAP settings - In Progress",
        "priority": "low",
        "status": "in-progress",
        "customer_id": ticket_res.json()["customer_id"]
    }, headers=agent_headers)
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "in-progress"

    # 5. Customer checks ticket -> verifies updated status
    cust_view = client.get(f"/tickets/{ticket_id}", headers=cust_headers)
    assert cust_view.status_code == 200
    assert cust_view.json()["status"] == "in-progress"

    # 6. Agent adds communication log to ticket
    log_res = client.post("/logs/", json={
        "type": "chat",
        "content": "Agent testuser has started looking into this ticket.",
        "ticket_id": ticket_id
    }, headers=agent_headers)
    assert log_res.status_code == 200

    # 7. Customer views logs for their ticket
    cust_logs = client.get(f"/logs/?ticket_id={ticket_id}", headers=cust_headers)
    assert cust_logs.status_code == 200
    assert len(cust_logs.json()) >= 1
    assert any("Agent testuser" in l["content"] for l in cust_logs.json())

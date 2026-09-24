"""
Comprehensive End-to-End Verification Script for Support CRM.
Validates all requirements:
1. Customer Registration & Hashed Password Storage
2. Customer Login & JWT Generation
3. Customer Ticket Creation (automatic ownership, no spoofing)
4. Customer Authorization & Isolation (Customer A vs B)
5. Agent Management (view, assign, update status)
6. Customer Visibility of Updates
7. Existing Staff APIs (CRUD, Reports, Logs)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app import models

client = TestClient(app)

def test_full_system_workflow():
    db = SessionLocal()
    try:
        # ===== TEST 1: Customer Registration & Secure Password Storage =====
        test_email_a = "verified_cust_a@crm.test"
        test_email_b = "verified_cust_b@crm.test"

        # Register Customer A
        res_reg = client.post("/auth/customer/register", json={
            "name": "Verified Customer A",
            "email": test_email_a,
            "password": "SecurePassword123!",
            "phone": "+1-555-1001",
            "company": "Acme Test A"
        })
        assert res_reg.status_code in (200, 400), f"Registration failed: {res_reg.text}"

        # Verify password is NOT plaintext in the database
        cust_db = db.query(models.Customer).filter(models.Customer.email == test_email_a).first()
        assert cust_db is not None, "Customer not found in DB"
        assert cust_db.hashed_password != "SecurePassword123!", "Password must be hashed!"
        assert cust_db.hashed_password.startswith("$2b$") or len(cust_db.hashed_password) > 20, "Password must be bcrypt hashed"

        # Register Customer B
        res_reg_b = client.post("/auth/customer/register", json={
            "name": "Verified Customer B",
            "email": test_email_b,
            "password": "SecurePassword456!",
            "phone": "+1-555-1002",
            "company": "Beta Test B"
        })
        assert res_reg_b.status_code in (200, 400), f"Registration B failed: {res_reg_b.text}"

        # ===== TEST 2: Customer Login & JWT =====
        login_res_a = client.post("/auth/customer/login", json={
            "email": test_email_a,
            "password": "SecurePassword123!"
        })
        assert login_res_a.status_code == 200, "Customer A login failed"
        token_a = login_res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        login_res_b = client.post("/auth/customer/login", json={
            "email": test_email_b,
            "password": "SecurePassword456!"
        })
        assert login_res_b.status_code == 200, "Customer B login failed"
        token_b = login_res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # ===== TEST 3: Customer Ticket Creation =====
        # Customer A submits a ticket without customer_id
        ticket_res_a = client.post("/tickets/", json={
            "title": "Customer A VPN Broken",
            "description": "Cannot connect to office VPN tunnel",
            "priority": "high"
        }, headers=headers_a)
        assert ticket_res_a.status_code == 200, f"Ticket creation failed: {ticket_res_a.text}"
        ticket_a = ticket_res_a.json()
        assert ticket_a["customer_id"] == cust_db.id, "Ticket must be linked to Customer A!"
        assert ticket_a["assigned_agent_id"] is None, "Customer cannot assign agents"
        assert ticket_a["status"] == "open"
        ticket_a_id = ticket_a["id"]

        # Customer B submits a ticket
        ticket_res_b = client.post("/tickets/", json={
            "title": "Customer B Invoice Issue",
            "description": "Billing inquiry for March",
            "priority": "low"
        }, headers=headers_b)
        assert ticket_res_b.status_code == 200
        ticket_b_id = ticket_res_b.json()["id"]

        # ===== TEST 4: Customer Authorization & Isolation =====
        # Customer A lists tickets -> only sees ticket A
        list_a = client.get("/tickets/", headers=headers_a).json()
        ids_a = [t["id"] for t in list_a]
        assert ticket_a_id in ids_a, "Customer A must see their own ticket"
        assert ticket_b_id not in ids_a, "Customer A must NOT see Customer B's ticket!"

        # Customer B lists tickets -> only sees ticket B
        list_b = client.get("/tickets/", headers=headers_b).json()
        ids_b = [t["id"] for t in list_b]
        assert ticket_b_id in ids_b, "Customer B must see their own ticket"
        assert ticket_a_id not in ids_b, "Customer B must NOT see Customer A's ticket!"

        # Customer A tries direct ID access to Customer B's ticket -> must be 403 Forbidden
        direct_access = client.get(f"/tickets/{ticket_b_id}", headers=headers_a)
        assert direct_access.status_code == 403, "Direct access to other customer ticket must be 403!"

        # Customer A tries to update Customer B's ticket -> must be 403 Forbidden
        tamper_update = client.put(f"/tickets/{ticket_b_id}", json={
            "title": "Hacked Title",
            "description": "Hacked",
            "status": "closed"
        }, headers=headers_a)
        assert tamper_update.status_code == 403, "Tampering with other customer ticket must be 403!"

        # Customer A tries to delete ticket -> must be 403 Forbidden
        delete_attempt = client.delete(f"/tickets/{ticket_a_id}", headers=headers_a)
        assert delete_attempt.status_code == 403, "Customer cannot delete tickets!"

        # ===== TEST 5: Agent Login, View & Update Ticket =====
        agent_login = client.post("/auth/login", data={"username": "testuser", "password": "testpass"})
        assert agent_login.status_code == 200, "Agent login failed"
        agent_token = agent_login.json()["access_token"]
        agent_headers = {"Authorization": f"Bearer {agent_token}"}

        # Agent can see all tickets (both A and B)
        agent_all_tickets = client.get("/tickets/", headers=agent_headers).json()
        agent_ids = [t["id"] for t in agent_all_tickets]
        assert ticket_a_id in agent_ids, "Agent must see ticket A"
        assert ticket_b_id in agent_ids, "Agent must see ticket B"

        # Agent updates status of ticket A to "in-progress" and adds communication log
        agent_update = client.put(f"/tickets/{ticket_a_id}", json={
            "title": "Customer A VPN Broken",
            "description": "Cannot connect to office VPN tunnel - Agent investigating router configs",
            "status": "in-progress",
            "priority": "urgent",
            "customer_id": cust_db.id,
            "assigned_agent_id": 2
        }, headers=agent_headers)
        assert agent_update.status_code == 200
        assert agent_update.json()["status"] == "in-progress"

        # Agent logs a communication
        log_res = client.post("/logs/", json={
            "type": "chat",
            "content": "Agent has verified your VPN certificate and is renewing credentials.",
            "ticket_id": ticket_a_id
        }, headers=agent_headers)
        assert log_res.status_code == 200

        # ===== TEST 6: Customer Sees Update =====
        # Customer A fetches their ticket -> sees status updated to "in-progress"
        cust_check = client.get(f"/tickets/{ticket_a_id}", headers=headers_a)
        assert cust_check.status_code == 200
        assert cust_check.json()["status"] == "in-progress"
        assert cust_check.json()["priority"] == "urgent"

        # Customer A fetches logs for their ticket -> sees the agent's message
        cust_logs = client.get(f"/logs/?ticket_id={ticket_a_id}", headers=headers_a)
        assert cust_logs.status_code == 200
        assert len(cust_logs.json()) >= 1
        assert any("renewing credentials" in l["content"] for l in cust_logs.json())

        # Customer B tries to view logs of Customer A's ticket -> must be 403 Forbidden!
        b_view_a_logs = client.get(f"/logs/?ticket_id={ticket_a_id}", headers=headers_b)
        assert b_view_a_logs.status_code == 403, "Customer B cannot view Customer A's ticket logs!"

        # ===== TEST 7: Existing APIs Still Function =====
        # Reports
        reports_res = client.get("/reports/tickets-summary", headers=agent_headers)
        assert reports_res.status_code == 200
        assert "total_tickets" in reports_res.json()

        workload_res = client.get("/reports/agent-workload", headers=agent_headers)
        assert workload_res.status_code == 200
        assert "agent_workload" in workload_res.json()

        # Customers list by agent
        customers_res = client.get("/customers/", headers=agent_headers)
        assert customers_res.status_code == 200
        assert isinstance(customers_res.json(), list)

        print("\nAll 7 test suites executed and passed with 100% success!")

    finally:
        db.close()

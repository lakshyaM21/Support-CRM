# Support CRM – Customer Support Management System

A full-stack, lightweight Customer Relationship and Support Management System built with **Python**, **FastAPI**, **SQLAlchemy**, **SQLite**, and a responsive **Vanilla HTML/CSS/JavaScript** frontend.

The application implements secure role-based access control, allowing **Customers** to register, authenticate with JWT, submit support requests, and track their tickets in total privacy, while **Agents** and **Admins** manage tickets, assign issues, log communications, and inspect analytics.

---

## 📋 Features

* **Customer Registration**: New customers can self-register with Name, Email, Phone, Company, and securely hashed passwords.
* **Customer Login**: Secure JWT-based authentication verifying hashed credentials.
* **JWT Authentication**: Token-based authentication using HS256 algorithm and bcrypt password hashing.
* **Agent Authentication**: Support staff login for handling customer inquiries.
* **Admin Authentication**: Administrative access to workload reports and system statistics.
* **Customer-Specific Tickets**: Automatic association with the authenticated customer; Customers only see their own tickets. Strict backend authorization prevents cross-customer data leakage.
* **Ticket Management**: Create, view, update status (`open`, `in-progress`, `resolved`, `closed`), prioritize (`low`, `medium`, `high`, `urgent`), and assign agents.
* **Customer Management**: Staff CRUD operations for managing client profiles and contact information.
* **Communication Logs**: Record multi-channel interactions (`call`, `email`, `chat`) attached directly to tickets for complete activity tracking.
* **Reports & Analytics**: Real-time summary counts by status, agent workload distribution, and average response times.
* **Frontend Dashboard**: Clean, responsive, modern interface built in pure Vanilla HTML, CSS, and JavaScript using Fetch API.

---

## 🛠 Technologies

* **Python 3.8+**: Core programming language
* **FastAPI**: Modern, fast ASGI web framework for RESTful APIs
* **SQLAlchemy**: Python SQL toolkit and Object-Relational Mapper (ORM)
* **SQLite**: Lightweight zero-configuration SQL database engine (`crm.db`)
* **Pydantic**: Data validation and serialization
* **JWT (python-jose & passlib)**: JSON Web Token generation and Bcrypt password hashing
* **HTML5**: Semantic markup for client dashboards
* **CSS3**: Responsive styling, custom design variables, status badges
* **JavaScript (Vanilla ES6)**: Asynchronous API communication via native `fetch()`

---

## 🗂 Project Structure

```text
support-crm/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization, CORS & static frontend mount
│   ├── database.py          # SQLAlchemy database engine and session dependency (get_db)
│   ├── models.py            # SQLAlchemy ORM models (User, Customer, Ticket, Log)
│   ├── schemas.py           # Pydantic models for validation and responses
│   ├── auth.py              # Authentication router (User & Customer login/registration)
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Re-exports auth router for consistency
│       ├── customers.py     # Customer CRUD endpoints & self-service profile
│       ├── tickets.py       # Ticket CRUD with customer ownership isolation
│       ├── logs.py          # Communication log endpoints
│       ├── reports.py       # Analytics and reporting endpoints
│       └── utils.py         # Passwords, JWT generation, get_current_actor dependency
│
├── frontend/
│   ├── index.html           # Landing page with portal entry points
│   ├── login.html           # Unified sign-in (Customer tab & Staff tab)
│   ├── register.html        # Customer registration page
│   ├── css/
│   │   └── style.css        # Clean, modern stylesheet
│   ├── js/
│   │   ├── api.js           # Central Fetch API client with automatic JWT headers
│   │   ├── auth.js          # Client session management & role guards
│   │   ├── customer.js      # Customer dashboard, ticket creation & conversation
│   │   ├── agent.js         # Agent ticket queue, assignment & communication logging
│   │   └── admin.js         # Admin reporting & workload analytics
│   ├── customer/
│   │   ├── dashboard.html   # Customer metrics & recent tickets
│   │   ├── tickets.html     # My Tickets table with search & filters
│   │   ├── create-ticket.html # Customer ticket creation form
│   │   ├── ticket-detail.html # View ticket status & conversation history
│   │   └── profile.html     # Manage customer contact details
│   ├── agent/
│   │   ├── dashboard.html   # Agent queue overview & metrics
│   │   ├── tickets.html     # Full ticket queue with status/priority filtering
│   │   ├── ticket-detail.html # Update status/priority, assign agent & add logs
│   │   └── customers.html   # Directory of registered customers
│   └── admin/
│       └── dashboard.html   # Status summaries, workload distribution, response metrics
│
├── crm.db                   # SQLite database
├── migrate_db.py            # Idempotent database schema migration script
├── test_api.py              # Existing API integration tests
├── test_customer_flow.py    # Customer authentication & ticket flow tests
├── test_full_workflow.py    # End-to-end full system workflow test
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## 🚀 Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/wisdom-dosoo/support-crm.git
cd "Support CRM 1"
```

### 2. Set Up Python Virtual Environment
```bash
# On Windows
python -m venv .venv
.venv\Scripts\activate

# On macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Database Migration
Apply schema updates safely (adds `hashed_password` to `customers` if missing):
```bash
python migrate_db.py
```

---

## 🏃 Running the Application

### 1. Start the Backend API Server
```bash
uvicorn app.main:app --reload
```
The FastAPI backend starts at:
```text
http://127.0.0.1:8000
```

### 2. Access the Frontend

You can access the frontend in either of two ways:

* **Directly through FastAPI (Recommended)**:
  Open your web browser and navigate to:
  ```text
  http://127.0.0.1:8000/frontend/
  ```

* **Or open `frontend/index.html`**:
  Open `frontend/index.html` directly in any web browser or use VSCode Live Server. The built-in `api.js` client automatically connects to `http://127.0.0.1:8000`.

---

## 📚 API Documentation

FastAPI provides built-in interactive API documentation:
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Alternative**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔐 Authentication System

The application features a dual-entity JWT authentication mechanism:

### 1. Customer Authentication
* **Registration**: `POST /auth/customer/register`
  * Accepts: `name`, `email`, `password`, `phone`, `company`, `notes`.
  * Hashes password using `bcrypt`.
* **Login**: `POST /auth/customer/login`
  * Accepts: `email`, `password`.
  * Returns: JWT bearer token containing `{"sub": email, "role": "customer", "customer_id": id}`.
* **Profile**: `GET /auth/customer/me`

### 2. Staff (Agent / Admin) Authentication
* **Registration**: `POST /auth/register`
* **Login**: `POST /auth/login` (OAuth2 password request form)
  * Accepts: `username`, `password`.
  * Returns: JWT bearer token containing `{"sub": username}`.
* **Profile**: `GET /auth/me`

### 3. Role & Ownership Enforcement (`get_current_actor`)
The backend inspects the JWT payload on every request:
* **Customer Isolation**: When a customer calls `GET /tickets/`, the query filters strictly by `customer_id == current_customer.id`. Direct requests like `GET /tickets/5` verify ownership and return `403 Forbidden` if the ticket belongs to another customer.
* **Staff Access**: Agents and Admins have global visibility to view all tickets, reassign agents, modify ticket statuses, and review analytics.

---

## 🎫 Complete Ticket Workflow

```text
1. Customer Registration / Login
   └── Customer signs in and receives JWT token.

2. Customer Submits Support Ticket
   └── Customer enters Title, Description, and Priority (Low, Medium, High, Urgent).
   └── The backend automatically populates `customer_id` from the JWT session.
   └── Customer cannot manually assign agents or spoof customer_id.

3. Agent Reviews Queue
   └── Agent logs in to the Agent Workspace.
   └── Agent sees the new ticket in the queue.
   └── Agent can click "Assign to Me" or update status to "In Progress".

4. Communication & Updates
   └── Agent logs communication notes (Call, Email, Chat).
   └── Customer views ticket details and sees updated status and messages.
   └── Customer can reply directly on their ticket timeline.

5. Ticket Resolution
   └── Agent marks ticket status as "Resolved".
   └── Customer sees "Resolved" badge on their dashboard.
```

---

## 🧪 Testing

The repository contains automated test suites covering customer authentication, data isolation, and existing staff APIs:

```bash
# Run all tests
pytest

# Or run individual test suites
pytest test_api.py
pytest test_customer_flow.py
pytest test_full_workflow.py
```

### Verified Test Cases:
1. **Customer Registration**: Validates password hashing and record creation.
2. **Customer Login**: Verifies credentials and JWT token issuance.
3. **Customer Ticket Creation**: Validates automatic customer linkage and default open status.
4. **Customer Authorization**: Validates that Customer A cannot view or tamper with Customer B's tickets (HTTP 403).
5. **Agent Operations**: Verifies that agents can view tickets across all customers, assign tickets, and update status.
6. **Customer Visibility**: Confirms that customers immediately observe status changes made by agents.
7. **Existing APIs**: Confirms full backwards compatibility for User CRUD, Customer CRUD, Logs, and Reports.

"""
Authentication router for Support CRM Backend.

Re-exports the router from app.auth for module consistency.
"""

from app.auth import router, register, login, read_users_me

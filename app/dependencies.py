from fastapi import Request
from .database import get_user, verify_password
import uuid

sessions = {}

def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        username = sessions[session_id]
        user = get_user(username)
        if user:
            return user
    return None

def is_admin(user) -> bool:
    return user and user["role"] == "admin"

def create_session(username: str) -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = username
    return session_id

def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user
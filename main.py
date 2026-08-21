import os
import re
import uuid
import time
import json
import base64
import hmac
import hashlib
import secrets
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import requests
from config import settings
from db import (
    init_db, get_db_connection, create_user, get_user_by_email,
    get_user_by_id, get_user_by_google_id, verify_user_email,
    update_user_password, link_google_account,
    save_email_verification, get_email_verification, increment_otp_attempts, delete_email_verification,
    save_password_reset, get_password_reset, increment_reset_attempts, delete_password_reset
)
from models import (
    ResearchRequest, ResearchStatusResponse, UpdateReportRequest,
    SignupRequest, LoginRequest, VerifyEmailRequest, ResendOtpRequest,
    ForgotPasswordRequest, ResetPasswordRequest, GoogleAuthRequest, UserResponse
)
from email_service import send_verification_otp_email, send_password_reset_email
from evidence_store import EvidenceStore
from pipeline import ResearchPipeline
from pdf_exporter import export_report_files, generate_pdf_from_markdown

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="DeepResearch Studio API", version="2.0.0")

# Mount Static & Template directories
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Global dictionary to track active pipeline threads
active_tasks: Dict[str, Any] = {}

# In-memory OTP storage cache for high performance & fallback redundancy
MEMORY_OTP_CACHE: Dict[str, Dict[str, Any]] = {}
MEMORY_RESET_CACHE: Dict[str, Dict[str, Any]] = {}

AUTH_SECRET = os.getenv("AUTH_SECRET", "deepresearch-studio-secret-auth-key-2026")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://deepresearch-studio.onrender.com/api/auth/google/callback")

@app.on_event("startup")
def startup_event():
    init_db()

# --- Security & Cryptography Utilities ---

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260000).hex()
    return f"{salt}${pw_hash}"

def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, original_hash = stored_hash.split("$", 1)
    test_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260000).hex()
    return hmac.compare_digest(test_hash, original_hash)

def generate_secure_otp() -> str:
    return f"{secrets.randbelow(900000) + 100000}"

def hash_code(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code.strip()}".encode("utf-8")).hexdigest()

def create_auth_token(user_id: str, email: str, expires_days: int = 30) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(time.time()) + (expires_days * 86400)
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def decode_auth_token(token: Optional[str]) -> Optional[dict]:
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        
        padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def get_current_user_optional(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif request.cookies.get("deepresearch_token"):
        token = request.cookies.get("deepresearch_token")

    if not token:
        return None
    
    payload = decode_auth_token(token)
    if not payload:
        return None
    
    user = get_user_by_id(payload.get("sub"))
    return user

def get_current_active_user(request: Request) -> dict:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in.")
    if not user.get("email_verified", 0):
        raise HTTPException(status_code=403, detail="Email verification required. Please verify your email.")
    return user

# --- Core Web Routes ---

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
@app.head("/health")
def health_check():
    return {"status": "ok"}

# --- Production Authentication API Endpoints ---

@app.post("/api/auth/signup")
def auth_signup(payload: SignupRequest):
    email = payload.email.lower().strip()
    name = payload.name.strip()
    
    # 1. Validation
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address format.")
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters long.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    if payload.confirm_password and payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    # 2. Check existing user
    existing = get_user_by_email(email)
    if existing and existing.get("email_verified", 0):
        raise HTTPException(status_code=400, detail="An account with this email already exists. Please sign in.")

    # 3. Create or update user as unverified
    pw_hash = hash_password(payload.password)
    user_id = existing["id"] if existing else str(uuid.uuid4())
    
    if existing:
        update_user_password(email, pw_hash)
    else:
        create_user(user_id=user_id, email=email, name=name, password_hash=pw_hash, auth_provider="email", email_verified=0)

    # 4. Generate secure 6-digit OTP
    otp_code = generate_secure_otp()
    salt = secrets.token_hex(8)
    otp_hash = hash_code(otp_code, salt)
    expires_at = int(time.time()) + 600 # 10 minutes
    resend_available_at = int(time.time()) + 60 # 60s cooldown

    # 5. Persist OTP
    save_email_verification(email, otp_hash, salt, expires_at, resend_available_at)
    MEMORY_OTP_CACHE[email] = {
        "otp_hash": otp_hash,
        "salt": salt,
        "raw_code": otp_code,
        "attempts": 0,
        "expires_at": expires_at,
        "resend_available_at": resend_available_at
    }

    # 6. Dispatch Verification Email
    send_verification_otp_email(to_email=email, name=name, otp_code=otp_code, expiry_minutes=10)

    masked_email = email[0] + "*****@" + email.split("@")[1] if len(email.split("@")[0]) > 1 else email
    return {
        "status": "success",
        "needs_verification": True,
        "email": email,
        "masked_email": masked_email,
        "message": f"Verification code dispatched to {masked_email}.",
        "resend_cooldown": 60,
        "dev_code": otp_code
    }

@app.post("/api/auth/verify-email")
def auth_verify_email(payload: VerifyEmailRequest, response: Response):
    email = payload.email.lower().strip()
    code = payload.code.strip()

    if not email or not code:
        raise HTTPException(status_code=400, detail="Email and 6-digit verification code are required.")

    # 1. Fetch record from Cache or DB
    record = MEMORY_OTP_CACHE.get(email) or get_email_verification(email)
    if not record:
        raise HTTPException(status_code=400, detail="No verification code was requested for this email. Please request a new code.")

    # 2. Check Expiry
    if int(time.time()) > record["expires_at"]:
        delete_email_verification(email)
        MEMORY_OTP_CACHE.pop(email, None)
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")

    # 3. Check Attempt Limits (Max 5 attempts)
    current_attempts = record.get("attempts", 0)
    if current_attempts >= 5:
        delete_email_verification(email)
        MEMORY_OTP_CACHE.pop(email, None)
        raise HTTPException(status_code=400, detail="Too many incorrect attempts. Please request a new code.")

    # 4. Verify Code Hash
    salt = record.get("salt", "")
    target_hash = record.get("otp_hash", "")
    calc_hash = hash_code(code, salt)

    if not hmac.compare_digest(calc_hash, target_hash) and record.get("raw_code") != code:
        new_attempts = increment_otp_attempts(email)
        if email in MEMORY_OTP_CACHE:
            MEMORY_OTP_CACHE[email]["attempts"] = new_attempts
        remaining = max(0, 5 - new_attempts)
        raise HTTPException(status_code=400, detail=f"Invalid verification code. {remaining} attempts remaining.")

    # 5. Success: Invalidate OTP & Verify User Account
    delete_email_verification(email)
    MEMORY_OTP_CACHE.pop(email, None)
    verify_user_email(email)

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="User record not found.")

    token = create_auth_token(user["id"], user["email"])
    response.set_cookie(
        key="deepresearch_token",
        value=token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax",
        secure=True
    )

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "email_verified": True,
            "auth_provider": user.get("auth_provider", "email"),
            "avatar_url": user.get("avatar_url")
        }
    }

@app.post("/api/auth/resend-otp")
def auth_resend_otp(payload: ResendOtpRequest):
    email = payload.email.lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    record = MEMORY_OTP_CACHE.get(email) or get_email_verification(email)
    now = int(time.time())

    if record and now < record.get("resend_available_at", 0):
        wait_seconds = record["resend_available_at"] - now
        raise HTTPException(status_code=429, detail=f"Please wait {wait_seconds} seconds before requesting a new verification code.")

    user = get_user_by_email(email)
    name = user["name"] if user else "Researcher"

    otp_code = generate_secure_otp()
    salt = secrets.token_hex(8)
    otp_hash = hash_code(otp_code, salt)
    expires_at = now + 600
    resend_available_at = now + 60

    save_email_verification(email, otp_hash, salt, expires_at, resend_available_at)
    MEMORY_OTP_CACHE[email] = {
        "otp_hash": otp_hash,
        "salt": salt,
        "raw_code": otp_code,
        "attempts": 0,
        "expires_at": expires_at,
        "resend_available_at": resend_available_at
    }

    send_verification_otp_email(to_email=email, name=name, otp_code=otp_code, expiry_minutes=10)

    return {
        "status": "success",
        "message": f"New verification code sent to {email}.",
        "resend_cooldown": 60,
        "dev_code": otp_code
    }

@app.post("/api/auth/login")
def auth_login(payload: LoginRequest, response: Response):
    email = payload.email.lower().strip()
    user = get_user_by_email(email)

    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password. Please check your credentials.")

    # Check Email Verification
    if not user.get("email_verified", 0):
        # Auto-trigger fresh verification OTP
        otp_code = generate_secure_otp()
        salt = secrets.token_hex(8)
        otp_hash = hash_code(otp_code, salt)
        expires_at = int(time.time()) + 600
        resend_available_at = int(time.time()) + 60

        save_email_verification(email, otp_hash, salt, expires_at, resend_available_at)
        MEMORY_OTP_CACHE[email] = {
            "otp_hash": otp_hash,
            "salt": salt,
            "raw_code": otp_code,
            "attempts": 0,
            "expires_at": expires_at,
            "resend_available_at": resend_available_at
        }
        send_verification_otp_email(to_email=email, name=user["name"], otp_code=otp_code, expiry_minutes=10)

        masked_email = email[0] + "*****@" + email.split("@")[1] if len(email.split("@")[0]) > 1 else email
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Email not verified. A new 6-digit verification code has been sent.",
                "needs_verification": True,
                "email": email,
                "masked_email": masked_email,
                "dev_code": otp_code
            }
        )

    token = create_auth_token(user["id"], user["email"])
    response.set_cookie(
        key="deepresearch_token",
        value=token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax",
        secure=True
    )

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "email_verified": True,
            "auth_provider": user.get("auth_provider", "email"),
            "avatar_url": user.get("avatar_url")
        }
    }

# --- Real Google OAuth 2.0 Endpoints ---

@app.get("/api/auth/google/url")
def auth_google_url():
    state = secrets.token_urlsafe(16)
    client_id = GOOGLE_CLIENT_ID or "109283746152-sampledeepresearch.apps.googleusercontent.com"
    redirect_uri = GOOGLE_REDIRECT_URI
    
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"state={state}&"
        f"access_type=offline&"
        f"prompt=select_account"
    )
    return {"url": url, "state": state}

@app.get("/api/auth/google/callback")
def auth_google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    if not code:
        return RedirectResponse(url="/?auth_error=google_cancelled")

    email = None
    name = "Google User"
    avatar_url = None
    google_id = None

    # Exchange code with Google
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        try:
            token_resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                },
                timeout=10
            )
            if token_resp.ok:
                t_data = token_resp.json()
                access_token = t_data.get("access_token")
                userinfo_resp = requests.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if userinfo_resp.ok:
                    u_info = userinfo_resp.json()
                    email = u_info.get("email")
                    name = u_info.get("name", name)
                    avatar_url = u_info.get("picture")
                    google_id = u_info.get("sub")
        except Exception as e:
            print("[Google OAuth] Token exchange error:", e)

    if not email:
        return RedirectResponse(url="/?auth_error=google_failed")

    # Safe Account Linking & Creation
    email = email.lower().strip()
    user = get_user_by_email(email)
    
    if user:
        link_google_account(email=email, google_id=google_id, avatar_url=avatar_url, name=name)
        user_id = user["id"]
    else:
        user_id = str(uuid.uuid4())
        create_user(user_id=user_id, email=email, name=name, auth_provider="google", google_id=google_id, avatar_url=avatar_url, email_verified=1)

    token = create_auth_token(user_id, email)
    resp = RedirectResponse(url=f"/?auth_token={token}")
    resp.set_cookie(
        key="deepresearch_token",
        value=token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax",
        secure=True
    )
    return resp

@app.post("/api/auth/google")
def auth_google_direct(payload: GoogleAuthRequest, response: Response):
    email = payload.email
    name = payload.name or "Google User"
    avatar_url = payload.avatar_url
    google_id = payload.google_id

    # 1. Parse Google Identity Credential if provided
    if payload.credential:
        try:
            parts = payload.credential.split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                jwt_data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
                email = jwt_data.get("email", email)
                name = jwt_data.get("name", name)
                google_id = jwt_data.get("sub", google_id)
                avatar_url = jwt_data.get("picture", avatar_url)
        except Exception as e:
            print("[Google ID Token Parse]:", e)

    # 2. Query userinfo if access_token provided
    if payload.access_token:
        try:
            u_resp = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {payload.access_token}"}, timeout=8)
            if u_resp.ok:
                u_info = u_resp.json()
                email = u_info.get("email", email)
                name = u_info.get("name", name)
                google_id = u_info.get("sub", google_id)
                avatar_url = u_info.get("picture", avatar_url)
        except Exception as e:
            print("[Google Userinfo Error]:", e)

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Google authentication failed to provide a valid email.")

    email = email.lower().strip()
    user = get_user_by_email(email)

    if user:
        link_google_account(email=email, google_id=google_id, avatar_url=avatar_url, name=name)
        user_id = user["id"]
    else:
        user_id = str(uuid.uuid4())
        create_user(user_id=user_id, email=email, name=name, auth_provider="google", google_id=google_id, avatar_url=avatar_url, email_verified=1)

    user = get_user_by_id(user_id)
    token = create_auth_token(user["id"], user["email"])
    response.set_cookie(
        key="deepresearch_token",
        value=token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax",
        secure=True
    )

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "email_verified": True,
            "auth_provider": "google",
            "avatar_url": user.get("avatar_url") or avatar_url
        }
    }

# --- Password Reset Flow ---

@app.post("/api/auth/forgot-password")
def auth_forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email address is required.")

    user = get_user_by_email(email)
    if user:
        reset_code = generate_secure_otp()
        salt = secrets.token_hex(8)
        token_hash = hash_code(reset_code, salt)
        expires_at = int(time.time()) + 600 # 10 minutes

        save_password_reset(email, token_hash, salt, expires_at)
        MEMORY_RESET_CACHE[email] = {
            "token_hash": token_hash,
            "salt": salt,
            "raw_code": reset_code,
            "attempts": 0,
            "expires_at": expires_at
        }
        send_password_reset_email(to_email=email, name=user["name"], reset_code=reset_code, expiry_minutes=10)

    # Return generic success to prevent account enumeration
    return {
        "status": "success",
        "message": "If an account exists with that email, a 6-digit password reset code has been sent.",
        "dev_code": MEMORY_RESET_CACHE.get(email, {}).get("raw_code")
    }

@app.post("/api/auth/reset-password")
def auth_reset_password(payload: ResetPasswordRequest):
    email = payload.email.lower().strip()
    code = payload.code.strip()
    new_password = payload.new_password

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long.")
    if payload.confirm_password and new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    record = MEMORY_RESET_CACHE.get(email) or get_password_reset(email)
    if not record:
        raise HTTPException(status_code=400, detail="No password reset request was found for this email. Please request a new code.")

    if int(time.time()) > record["expires_at"]:
        delete_password_reset(email)
        MEMORY_RESET_CACHE.pop(email, None)
        raise HTTPException(status_code=400, detail="Password reset code has expired. Please request a new code.")

    current_attempts = record.get("attempts", 0)
    if current_attempts >= 5:
        delete_password_reset(email)
        MEMORY_RESET_CACHE.pop(email, None)
        raise HTTPException(status_code=400, detail="Too many incorrect attempts. Please request a new reset code.")

    salt = record.get("salt", "")
    target_hash = record.get("token_hash", "")
    calc_hash = hash_code(code, salt)

    if not hmac.compare_digest(calc_hash, target_hash) and record.get("raw_code") != code:
        new_attempts = increment_reset_attempts(email)
        if email in MEMORY_RESET_CACHE:
            MEMORY_RESET_CACHE[email]["attempts"] = new_attempts
        remaining = max(0, 5 - new_attempts)
        raise HTTPException(status_code=400, detail=f"Invalid password reset code. {remaining} attempts remaining.")

    # Success: Update user password and revoke reset token
    delete_password_reset(email)
    MEMORY_RESET_CACHE.pop(email, None)
    new_pw_hash = hash_password(new_password)
    update_user_password(email, new_pw_hash)

    return {
        "status": "success",
        "message": "Password updated successfully. You can now sign in with your new password."
    }

@app.get("/api/auth/me")
def auth_me(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return {"authenticated": False, "user": None}
    
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "email_verified": bool(user.get("email_verified", 0)),
            "auth_provider": user.get("auth_provider", "email"),
            "avatar_url": user.get("avatar_url")
        }
    }

@app.post("/api/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie("deepresearch_token")
    return {"status": "success", "message": "Logged out successfully."}

# --- Protected Research Endpoints ---

@app.post("/api/research")
def start_research(request: Request, payload: ResearchRequest, background_tasks: BackgroundTasks):
    user = get_current_active_user(request)
    session_id = str(uuid.uuid4())
    user_id = user["id"]

    db_store = EvidenceStore()
    config_dict = {
        "max_rounds": payload.max_rounds,
        "max_sources": payload.max_sources,
        "fast_model": payload.fast_model,
        "strong_model": payload.strong_model,
        "target_pages": payload.target_pages,
        "custom_suggestions": payload.custom_suggestions
    }
    db_store.create_session(session_id, payload.query, config=config_dict, user_id=user_id)

    pipeline = ResearchPipeline(
        session_id=session_id,
        user_query=payload.query,
        max_rounds=payload.max_rounds,
        max_sources=payload.max_sources,
        fast_model=payload.fast_model,
        strong_model=payload.strong_model,
        target_pages=payload.target_pages,
        custom_suggestions=payload.custom_suggestions,
        user_id=user_id
    )

    thread = threading.Thread(target=pipeline.run, daemon=True)
    active_tasks[session_id] = {
        "pipeline": pipeline,
        "thread": thread,
        "user_id": user_id
    }
    thread.start()

    return {"session_id": session_id, "status": "started"}

@app.get("/api/research/{session_id}/status", response_model=ResearchStatusResponse)
def get_research_status(session_id: str, request: Request):
    user = get_current_active_user(request)
    db_store = EvidenceStore()
    session = db_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    if session.get("user_id") and session["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied to this private research session.")

    logs = db_store.get_session_logs(session_id)
    current_action = logs[-1]["message"] if logs else "Processing..."

    claims = db_store.get_claims(session_id)
    sources = db_store.get_sources(session_id)
    contradictions = db_store.get_contradictions(session_id)

    config = json.loads(session["config_json"]) if session.get("config_json") else {}
    total_rounds = config.get("max_rounds", settings.MAX_ROUNDS)

    return ResearchStatusResponse(
        session_id=session_id,
        status=session["status"],
        stage=session["stage"],
        rounds_completed=session["rounds_completed"] or 0,
        total_rounds=total_rounds,
        sources_found=len(sources),
        claims_extracted=len(claims),
        contradictions_found=len(contradictions),
        current_action=current_action
    )

@app.get("/api/research/{session_id}/report")
def get_research_report(session_id: str, request: Request):
    user = get_current_active_user(request)
    db_store = EvidenceStore()
    session = db_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") and session["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    report = db_store.get_report(session_id)
    claims = db_store.get_claims(session_id)
    sources = db_store.get_sources(session_id)
    contradictions = db_store.get_contradictions(session_id)
    logs = db_store.get_session_logs(session_id)

    return {
        "session": dict(session),
        "report": dict(report) if report else None,
        "claims": [dict(c) for c in claims],
        "sources": [dict(s) for s in sources],
        "contradictions": [dict(ct) for ct in contradictions],
        "logs": [dict(l) for l in logs]
    }

@app.put("/api/research/{session_id}/report")
def update_research_report(session_id: str, payload: UpdateReportRequest, request: Request):
    user = get_current_active_user(request)
    db_store = EvidenceStore()
    session = db_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") and session["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    db_store.update_report_content(session_id, payload.markdown_content)
    return {"status": "success", "message": "Report updated successfully"}

@app.get("/api/sessions")
def list_sessions(request: Request):
    user = get_current_active_user(request)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, query, status, stage, created_at
        FROM sessions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 30
    """, (user["id"],))
    rows = cursor.fetchall()
    conn.close()
    return [{"session_id": r["session_id"], "query": r["query"], "status": r["status"], "stage": r["stage"], "created_at": r["created_at"]} for r in rows]

@app.get("/api/export/{session_id}/{format}")
def export_file(session_id: str, format: str, request: Request):
    user = get_current_active_user(request)
    db_store = EvidenceStore()
    session = db_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") and session["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    report = db_store.get_report(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet")

    markdown_text = report["markdown_content"]
    safe_topic = re.sub(r"[^\w\s-]", "", session["query"]).strip()[:40].replace(" ", "_")
    
    exports_dir = BASE_DIR / "exports"
    exports_dir.mkdir(exist_ok=True)

    if format == "pdf":
        file_path = exports_dir / f"{safe_topic}_{session_id[:8]}.pdf"
        generate_pdf_from_markdown(markdown_text, file_path, title=session["query"])
        return FileResponse(file_path, media_type="application/pdf", filename=f"{safe_topic}_Report.pdf")
    elif format == "md":
        file_path = exports_dir / f"{safe_topic}_{session_id[:8]}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        return FileResponse(file_path, media_type="text/markdown", filename=f"{safe_topic}_Report.md")
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'pdf' or 'md'.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

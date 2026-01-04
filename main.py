from fastapi import FastAPI, HTTPException, Request, Depends, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import os
import re
import logging
from sshtunnel import SSHTunnelForwarder
import io
import aiomysql
from typing import Optional, List
import certifi

# Internal imports
from utils.config import Config
from utils.response_formatter import ResponseFormatter
from db.mariadb_client import MariaDBClient
from agents.query_optimizer import optimize_query
from agents.cost_advisor import estimate_cost
from agents.schema_advisor import advise_schema
from agents.data_validator import validate_query
from utils.auth_utils import get_password_hash, verify_password, create_access_token, decode_access_token

# Logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="QueryVault Enterprise")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from motor.motor_asyncio import AsyncIOMotorClient
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from bson import ObjectId

# --- Database Helper for App Data (MongoDB) ---
mongo_client = AsyncIOMotorClient(
    os.getenv("MONGO_URI", "mongodb://localhost:27017"),
    tlsCAFile=certifi.where()
)
db = mongo_client[os.getenv("MONGO_DB_NAME", "queryvault_db")]

# --- Mail Configuration ---
mail_conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
fastmail = FastMail(mail_conf)

# --- Authentication Dependency ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

async def get_current_user(request: Request):
    logger.info("Checking current user")
    token = request.cookies.get("access_token")
    if not token:
        logger.info("No token found")
        return None
    
    if token.startswith("Bearer "):
        token = token[7:]
    
    payload = decode_access_token(token)
    if not payload:
        logger.info("Invalid token payload")
        return None
    
    email = payload.get("sub")
    logger.info(f"Fetching user for email: {email}")
    user = await db.users.find_one({"email": email})
    if user:
        user["id"] = str(user.pop("_id")) # Convert ObjectId to string and rename key
    return user

# --- Pydantic Models ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class SSHConfig(BaseModel):
    host: str
    port: int = 22
    user: str
    password: Optional[str] = None
    private_key: Optional[str] = None

class DatabaseConfig(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str
    database: str
    use_ssh: bool = False
    ssh_config: Optional[SSHConfig] = None

class QueryRequest(BaseModel):
    sql: str
    database: DatabaseConfig
    run_in_sandbox: bool = True

class SchemaRequest(BaseModel):
    database: DatabaseConfig

# --- Helper Logic ---
async def get_connection_details(db_config: DatabaseConfig):
    tunnel = None
    host = db_config.host
    port = db_config.port

    if db_config.use_ssh and db_config.ssh_config:
        ssh_cfg = db_config.ssh_config
        tunnel_kwargs = {
            "ssh_address_or_host": (ssh_cfg.host, ssh_cfg.port),
            "ssh_username": ssh_cfg.user,
            "remote_bind_address": (db_config.host, db_config.port),
        }
        if ssh_cfg.private_key:
            tunnel_kwargs["ssh_pkey"] = io.StringIO(ssh_cfg.private_key)
        else:
            tunnel_kwargs["ssh_password"] = ssh_cfg.password

        tunnel = SSHTunnelForwarder(**tunnel_kwargs)
        tunnel.start()
        host = "127.0.0.1"
        port = tunnel.local_bind_port

    db_client = MariaDBClient(
        host=db_config.host,
        user=db_config.user,
        password=db_config.password,
        database=db_config.database,
        port=db_config.port
    )
    return db_client, tunnel, host, port

# --- AUTH ENDPOINTS ---
@app.post("/auth/register")
async def register(user: UserRegister):
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Identity already registered")
    
    hashed_pw = get_password_hash(user.password)
    await db.users.insert_one({
        "email": user.email,
        "hashed_password": hashed_pw,
        "full_name": user.full_name,
        "created_at": datetime.utcnow()
    })
    return {"status": "success"}

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"email": form_data.username})

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid neural key")

    access_token = create_access_token(data={"sub": user["email"]})
    response = RedirectResponse(url="/studio", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.post("/auth/forgot-password")
async def forgot_password(request: Request):
    data = await request.json()
    email = data.get("email")
    user = await db.users.find_one({"email": email})
    
    if user:
        # In a real app, generate a unique token and save it to DB
        reset_token = create_access_token(data={"sub": email, "type": "reset"}, expires_delta=timedelta(minutes=30))
        reset_link = f"{request.base_url}reset-password?token={reset_token}"
        
        message = MessageSchema(
            subject="QueryVault Emergency Access Reset",
            recipients=[email],
            body=f"Neural identity recovery initiated. Use this link to reset your access key: {reset_link}",
            subtype=MessageType.plain
        )
        await fastmail.send_message(message)
    
    return {"message": "If this identity exists, a recovery signal has been broadcasted."}

@app.get("/auth/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

# --- PAGE ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request, user=Depends(get_current_user)):
    logger.info("Accessing home page")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user=Depends(get_current_user)):
    if user: return RedirectResponse("/studio")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user=Depends(get_current_user)):
    if user: return RedirectResponse("/studio")
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@app.post("/auth/reset-password")
async def reset_password(request: Request):
    data = await request.json()
    token = data.get("token")
    new_password = data.get("password")
    
    payload = decode_access_token(token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired recovery signal")
    
    email = payload.get("sub")
    hashed_pw = get_password_hash(new_password)
    
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"hashed_password": hashed_pw}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Identity not found")
        
    return {"message": "Access key updated successfully. Return to login."}

@app.get("/studio", response_class=HTMLResponse)
async def studio_page(request: Request, user=Depends(get_current_user)):
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("studio.html", {"request": request, "user": user})

@app.get("/vault", response_class=HTMLResponse)
async def vault_page(request: Request, user=Depends(get_current_user)):
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("vault.html", {"request": request, "user": user})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("about.html", {"request": request, "user": user})

# --- ANALYSIS ENDPOINTS ---
@app.post("/analyze")
async def analyze(request: QueryRequest, user=Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    query = request.sql.strip()
    db_client, tunnel, host, port = await get_connection_details(request.database)
    try:
        await db_client.connect(host=host, port=port)
        schema_context = await db_client.get_schema_context(query)
        explain_plan = await db_client.explain(query) if query.lower().startswith("select") else {}
        sample_rows = await db_client.fetch_sample_rows(query) if query.lower().startswith("select") else {}
        
        opt = await optimize_query(query, schema_context, explain_plan, sample_rows)
        cost = await estimate_cost(query, explain_plan)
        schema_adv = await advise_schema(query, schema_context)
        data_val = await validate_query(query, sample_rows)

        return ResponseFormatter.format_analysis(
            query, schema_context, explain_plan, sample_rows, opt, cost, schema_adv, data_val, request.database.database
        )
    finally:
        await db_client.disconnect()
        if tunnel: tunnel.stop()

@app.post("/analyze-schema")
async def analyze_schema(request: SchemaRequest, user=Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    db_client, tunnel, host, port = await get_connection_details(request.database)
    try:
        await db_client.connect(host=host, port=port)
        return {"database": request.database.database, "tables": await db_client.get_full_schema()}
    finally:
        await db_client.disconnect()
        if tunnel: tunnel.stop()

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

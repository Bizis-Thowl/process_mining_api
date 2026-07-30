from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import os
#import json
from fastapi import Depends, FastAPI, HTTPException, status
#from fastapi import File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel

from fastapi.openapi.utils import get_openapi

from user_management import UserManager, NewPasswordForm

from process_mining_api.test import test
from process_mining_api.process_mining_test import simple_bpmn
from process_mining_api.llm_response import QueryHandler

#from database import fake_users_db

# FastAPI App initialisieren
app = FastAPI()

query_handler = QueryHandler()

# Configuration

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="KI-InnOMATiV LLM API",
        version="0.1.0",
        summary="An API for the **KI-InnOMATiV** project",
        description="This API is part of the **KI-InnOMATiV** project and offers several functionalities for LLM usage.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30


user_manager = UserManager()
user_db = user_manager.get_user_db()

# Security

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(user_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(user_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me/")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    return current_user


@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return [{"item_id": "Foo", "owner": current_user.username}]

@app.post("/users/me/change_password/")
async def change_password(
    form_data: Annotated[NewPasswordForm, Depends()] 
):
    user = authenticate_user(user_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if form_data.new_password != form_data.new_password_repeat:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    else:
        new_hash = get_password_hash(form_data.new_password)
        new_hash_rep = get_password_hash(form_data.new_password_repeat)
        user_db[form_data.username]["hashed_password"] = new_hash
        user_manager.update_user_db(user_db)
      

"""
async def change_password(
    current_user: Annotated[User, Depends(get_current_active_user)], old_password: str, new_password: str, new_password_repeat: str):
    authenticate_user(user_db, current_user["username"], old_password)
    new_hash = get_password_hash(new_password)
    new_hash_rep = get_password_hash(new_password_repeat)
    if new_hash != new_hash_rep:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    else:
        user_db[current_user["username"]]["hashed_password"] = new_hash
        user_manager.update_user_db(user_db)"""
        

# Logic for answering queries

# Request-Body definieren
class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True

# Einfacher GET Endpoint
@app.get("/")
def root():
    return {"message": "Hello FastAPI", "test": test()}

# GET mit Path-Parameter
@app.get("/items/{item_id}")
def get_item(item_id: int, current_user: Annotated[User, Depends(get_current_active_user)]):
    return {"item_id": item_id}

# POST Endpoint mit JSON Body
@app.post("/items")
def create_item(item: Item, current_user: Annotated[User, Depends(get_current_active_user)]):
    return {
        "message": "Item received",
        "data": item
    }

#@app.post("/upload_csv/")
#async def upload_csv_file(file: UploadFile = File(...)):
#    contents = await file.read()
#    return simple_bpmn(contents, file.filename)

@app.get("/query")
async def get_query(query: str, current_user: Annotated[User, Depends(get_current_active_user)]):
    response = query_handler.simple_query(query)
    return {"query": query, "response": response}

@app.get("/question")
def get_answer(query: str, current_user: Annotated[User, Depends(get_current_active_user)]):
    response = query_handler.simple_question(query)
    return {"query": query, "response": response}

@app.get("/change_tracing_id")
def change_tracing_id(tracing_id: str, current_user: Annotated[User, Depends(get_current_active_user)]):
    query_handler.set_tracing_id(tracing_id)
    return {"message": f"Tracing ID changed to {tracing_id}"}

@app.get("/test")
def test_model(query: str, current_user: Annotated[User, Depends(get_current_active_user)], model:str = "Qwen/Qwen3.6-27B-FP8"):
    response = query_handler.test_model(query, model)
    return {"query": query, "response": response}

@app.get("/test_persona")
def test_persona_with_model(query: str, persona: str, current_user: Annotated[User, Depends(get_current_active_user)],model: str = "Qwen/Qwen3.6-27B-FP8"):
    response = query_handler.test_persona(query, persona, model)
    return {"query": query, "persona": persona, "response": response}
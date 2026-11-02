from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import os

from fastapi import Depends, FastAPI, Response, HTTPException, status
#from fastapi import File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, PlainTextResponse

from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel

from fastapi.openapi.utils import get_openapi

from user_management import UserManager, NewPasswordForm

from process_mining_api.test import test
from process_mining_api.process_mining_test import simple_bpmn
from process_mining_api.llm_response import QueryHandler #, ModelHandler

#from database import fake_users_db

##################################
# OpenAPI-Documentation
##################################


tags_metadata = [
    {
        "name": "users",
        "description": "Operations with users. The **login** logic is also here.",
    },
    {
        "name": "queries",
        "description": "The user-queries are in this section.",
    },
    {
        "name": "chunks",
        "description": "Operations for adding, deleting and updating the Chunk-Database",
    },
    {
        "name": "models",
        "description": "All the functions that are related to the models",
    }
]

description = """
This API is part of the **KI-InnOMATiV** project and offers several functionalities for LLM usage.

<details>
<summary>This is the current status on the implementation of the methods:</summary>

||Method|Status|
|------|-------|-------|
| &#x2705; | /token | Done |
| &#x2705; | /users/me/change_password | Done |
| &#x2705; | /models | Done |
| &#x2705; | PUT /chunks/\{chunk_id\} | Done |
| &#x2705; | DELETE /chunks/\{chunk_id\} | Done |
| &#x2705; | /user_query | Done |
| &#x2705; | GET /chunks/\{chunk_id\} | Done |
| &#x274c; | GET /chunks |In progress |
| &#x274c; | DELETE /chunks |In progress |
| &#x274c; | GET /chunks/batch |In progress |
| &#x274c; | DELETE /chunks/batch |In progress |


</details>
"""

# FastAPI App initialisieren
app = FastAPI(title="KI-InnOMATiV LLM API",
        version="0.4.0",
        description=description,
        openapi_tags=tags_metadata)

query_handler = QueryHandler()

##################################
# Redirect to landing page
##################################

@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url='/docs')

##################################
# RESPONSES
##################################

#def responses(*code: int, **description: str):
#    return {code: {"description": description}}


###################################
# Security
###################################

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30


user_manager = UserManager()
user_db = user_manager.get_user_db()

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


@app.post("/token", tags=["users"])
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


    
@app.post("/users/me/change_password/", tags=["users"])
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
class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True"""

#################################
# CLASSES
#################################

class Document(BaseModel):
    doc_id: int
    chunks: list[str]

class SearchCriteria(BaseModel):
    source_ids: list[str] = []
    user_roles: list[str] = []

class UserQuery(BaseModel):
    query: str
    session_id: int
    model:str = "google/gemma-4-26B-A4B-it"
    with_doc_search: bool = False
    search_criteria: SearchCriteria = None
    documents: list[Document] = None
    persona: str = None
    tracing_id:str = None

class Chunk(BaseModel):
    """
    Contains all the information for a chunk. Does not contain a Chunk-id.
    """
    text: str
    role_access: list[str]
    source_id: str = None
    collection_name: str = "Default_collection"

class QueryResponse(BaseModel):
    query_id: str
    session_id: int
    text: str
    retrieved_chunks: list[str] = None

class CompleteChunk(BaseModel):
    """
    Contains a Chunk and Chunk-id
    """
    chunk_id: str
    chunk: Chunk

class Model(BaseModel):
    name: str 
    description: str
    max_input_tokens: int
    max_output_tokens: int
    multimodal: bool
    additional_info: str

#################################
# QUERIES
#################################


@app.post("/user_query", tags=["queries"])
def user_query(
    user_query: UserQuery,
    current_user: Annotated[User, Depends(get_current_active_user)]
    )-> QueryResponse:
    #Error handling
    context_overflow = False
    wrong_modelname = False
    if context_overflow:
        raise HTTPException(status_code=413, detail="Context overflow: The model cannot handle the size of this request.")
    wrong_modelname = False
    if wrong_modelname:
        raise HTTPException(status_code=400, detail="The modelname is wrong")
    if user_query.persona is None:
        user_query.persona = "Du bis ein hilfsbereites Sprachmodell"
    full_response = query_handler.user_query(user_query=user_query)
    response = full_response[0]
    chunk_ids= full_response[1]
    print("Chunk_ids: ",chunk_ids)
    #query_handler.test_persona(user_query.query, user_query.model, user_query.persona)
    return {"query_id": "Dummy_id", "session_id": user_query.session_id, "text":response.model_dump_json(),"retrieved_chunks": chunk_ids}



#################################
# CHUNKS
#################################

@app.get("/chunks", tags=["chunks"], summary="Get chunks",
         description="Gets the chunks whose source ID matches an entry of `source_ids`, or all chunks if absent. The entries contain no text.",
         response_description="The matching chunks; empty if none match.",
            responses={200: {"description": "Returns list of complete chunks"}, 404: {"description": "Source_id(s) not found"}})
async def get_chunks(source_ids: list[str], current_user: Annotated[User, Depends(get_current_active_user)]) -> list[CompleteChunk]:
    pass


@app.delete("/chunks", tags=["chunks"], operation_id="deleteChunks", summary="Delete chunks",
            description="Deletes the chunks whose source ID matches an entry of `source_ids`, or all chunks if absent.",
            responses={200: {"description": "Successfully deleted"}, 404: {"description": "Source_id(s) not found"}})
async def delete_chunks(source_ids: list[str], current_user: Annotated[User, Depends(get_current_active_user)]) -> PlainTextResponse:
    pass

@app.post("/chunks/batch", tags=["chunks"], summary="Store chunks",
          description="Creates each chunk of the list or replaces it completely. All or nothing: if one entry is invalid or a `chunk_id` occurs twice, no chunk is stored.",
            responses={200: {"description": "Chunks successfully updated!"}, 201: {"description": "Chunks successfully created!"},
                       400: {"description": "Bad request"}})
async def update_chunks(chunks: list[CompleteChunk], current_user: Annotated[User, Depends(get_current_active_user)]) -> PlainTextResponse:
    return "This method is not implemented yet"
 
 
@app.delete("/chunks/batch", tags=["chunks"], operation_id="deleteChunksById", summary="Delete chunks",
            description="Deletes each existing chunk of the list. Unknown IDs are skipped.",
            responses={200: {"description": "Successfully deleted"}, 404: {"description": "Chunk_id(s) not found"}})
async def batch_delete_chunks(chunk_ids: list[str], current_user: Annotated[User, Depends(get_current_active_user)]) -> PlainTextResponse:
    return PlainTextResponse(content= "This method is not implemented yet",status_code=418)


@app.put("/chunks/{chunk_id}", tags=["chunks"],status_code=status.HTTP_201_CREATED,
            responses={200: {"description": "Chunk with the id [chunk_id] successfully updated!"}, 201: {"description": "Chunk with the id [chunk_id] successfully created!"},
                       500: {"description": "Internal server error"}})
def update_chunk(chunk_id, chunk:Chunk, current_user: Annotated[User, Depends(get_current_active_user)], response: Response):
    try:
        was_updated = query_handler.update_chunk(chunk_id, chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if was_updated:
        response.status_code = status.HTTP_200_OK
        return "Chunk with the id "+chunk_id+" successfully updated!"
    else:    
        return "Chunk with the id "+chunk_id+" successfully created!"


@app.get("/chunks/{chunk_id}", tags=["chunks"],
        responses={200: {"description": "Returns complete chunk"}, 404: {"description": "Chunk_id not found"}})
def get_chunk(
    chunk_id:str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    collection_name: str = "Default_collection" 
    )-> CompleteChunk:
    response = query_handler.get_chunk(collection_name=collection_name, chunk_id=chunk_id)
    if response is None:
            raise HTTPException(status_code=404, detail="Chunk not found.")
    text = response.payload["page_content"]
    role_access = response.payload["metadata"]["role_access"]
    source_id = response.payload["metadata"]["source_id"]
    collection_name = collection_name
    return {"chunk_id": chunk_id, "chunk": {"text":text,"role_access":role_access,"source_id":source_id,"collection_name":collection_name}}



@app.delete("/chunks/{chunk_id}", tags=["chunks"],
            responses={200: {"description": "Successfully deleted"}, 404: {"description": "Chunk_id not found"}})
def delete_chunk(chunk_id:str, current_user: Annotated[User, Depends(get_current_active_user)]):
    was_deleted = query_handler.delete_chunk(chunk_id)
    if was_deleted is False:
        raise HTTPException(status_code=404, detail="Chunk not found.")
    return "Chunk with the id "+chunk_id+" successfully deleted!"


#################################
# MODELS
#################################


@app.get("/models", tags=["models"])
async def models(
    current_user: Annotated[User, Depends(get_current_active_user)]
    )-> list[Model]:
    models = query_handler.get_models()
    return models


from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from process_mining_api.test import test
from process_mining_api.process_mining_test import simple_bpmn
from process_mining_api.responsemodels.query import Query
from process_mining_api.llm_response import answer_query

# FastAPI App initialisieren
app = FastAPI()

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
def get_item(item_id: int):
    return {"item_id": item_id}

# POST Endpoint mit JSON Body
@app.post("/items")
def create_item(item: Item):
    return {
        "message": "Item received",
        "data": item
    }

@app.post("/upload_csv/")
async def upload_csv_file(file: UploadFile = File(...)):
    contents = await file.read()
    return simple_bpmn(contents, file.filename)

@app.get("/query/{query_id}")
def get_query(query_id: int, query: Query):
    response = answer_query(query["full_text"])
    return {"query_id": query_id, "response": response}
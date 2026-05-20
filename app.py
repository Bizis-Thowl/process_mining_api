from fastapi import FastAPI
from pydantic import BaseModel

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
    return {"message": "Hello FastAPI"}

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
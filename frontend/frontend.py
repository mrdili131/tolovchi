from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter(include_in_schema=False)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def template(file_name: str):
    file_url = os.path.join(BASE_DIR, "templates", file_name)
    return FileResponse(file_url)

@router.get('/')
def home():
    return template("index.html")

@router.get('/oferta')
def oferta():
    return template("oferta.html")

@router.get('/printables')
def printables():
    return template("printables.html")
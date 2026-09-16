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
    return template("welcome.html")

@router.get('/auth')
def auth_page():
    return template("auth.html")

@router.get('/dashboard')
def dashboard_page():
    return template("dashboard.html")

@router.get('/dashboard/cards')
def dashboard_cards_page():
    return template("cards.html")

@router.get('/dashboard/applications')
def dashboard_applications_page():
    return template("applications.html")

@router.get('/dashboard/transactions')
def dashboard_transactions_page():
    return template("transactions.html")

@router.get('/info')
def info_page():
    return template("info.html")

@router.get('/oferta')
def oferta():
    return template("oferta.html")

@router.get('/printables')
def printables():
    return template("printables.html")
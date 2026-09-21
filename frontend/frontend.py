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

@router.get('/dashboard/payouts')
def dashboard_payouts_page():
    return template("payouts.html")

@router.get('/developer')
def developer_page():
    return template("developer.html")

@router.get('/api-docs')
def api_docs_page():
    return template("api-docs.html")

@router.get('/admin')
def admin_page():
    return template("admin.html")

@router.get('/admin/users')
def admin_users_page():
    return template("admin-users.html")

@router.get('/admin/applications')
def admin_applications_page():
    return template("admin-applications.html")

@router.get('/admin/transactions')
def admin_transactions_page():
    return template("admin-transactions.html")

@router.get('/admin/cards')
def admin_cards_page():
    return template("admin-cards.html")

@router.get('/admin/logs')
def admin_logs_page():
    return template("admin-logs.html")

@router.get('/admin/payouts')
def admin_payouts_page():
    return template("admin-payouts.html")

@router.get('/notifications')
def notifications_page():
    return template("notifications.html")

@router.get('/info')
def info_page():
    return template("info.html")

@router.get('/oferta')
def oferta():
    return template("oferta.html")

@router.get('/printables')
def printables():
    return template("printables.html")
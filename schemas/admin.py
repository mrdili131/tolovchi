from pydantic import BaseModel


class PlatformStatsResponse(BaseModel):
    total_users: int
    total_services: int
    total_admins: int
    active_applications: int
    total_applications: int
    total_transactions: int
    total_volume: int
    active_cards: int
    active_api_keys: int

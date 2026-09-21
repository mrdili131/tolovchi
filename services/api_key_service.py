import secrets
import hashlib
from datetime import datetime
from sqlalchemy import select
from models import ApiKey

KEY_PREFIX = "bnd_live_"


def generate_api_key() -> tuple[str, str, str]:
    raw_key = f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"
    prefix = raw_key[: len(KEY_PREFIX) + 8]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, prefix, key_hash


async def get_service_by_api_key(api_key: str, db) -> ApiKey | None:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    db_key = await db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True))

    if not db_key:
        return None

    db_key.last_used_at = datetime.utcnow().date()
    await db.commit()
    await db.refresh(db_key)

    return db_key

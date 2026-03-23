from typing import Optional
from supabase import Client, create_client
from app.settings import settings


def get_supabase_client() -> Optional[Client]:
    if not settings.supabase_url:
        return None

    key = settings.supabase_service_role_key or settings.supabase_anon_key
    if not key:
        return None

    client = create_client(settings.supabase_url, key)
    if settings.supabase_schema:
        client.postgrest.schema(settings.supabase_schema)
    return client

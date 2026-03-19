import os
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url:
    raise ValueError("SUPABASE_URL is missing")
if not key:
    raise ValueError("SUPABASE_KEY is missing")

supabase_client = create_client(url, key)

import pandas as pd
from supabase import create_client, Client

from src.config import SUPABASE_URL, SUPABASE_KEY


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_listings(client: Client) -> pd.DataFrame:
    """Load active listings from property_listings."""
    response = (
        client.table("property_listings")
        .select("id, state, neighborhood, price, photo_count, listed_at, status, listing_url")
        .eq("status", "active")
        .execute()
    )
    return pd.DataFrame(response.data)


def save_opportunities(df: pd.DataFrame, client: Client) -> None:
    """Upsert results into listing_opportunities."""
    records = df.to_dict(orient="records")

    # Convert numpy/pandas types to native Python for JSON serialization
    for rec in records:
        for k, v in rec.items():
            if hasattr(v, "item"):       # numpy scalar
                rec[k] = v.item()
            elif hasattr(v, "isoformat"): # datetime/Timestamp
                rec[k] = v.isoformat()

    client.table("listing_opportunities").upsert(records).execute()


def fetch_opportunities(client: Client) -> pd.DataFrame:
    """Load computed opportunities ordered by score (used by dashboard)."""
    response = (
        client.table("listing_opportunities")
        .select("*")
        .order("opportunity_score", desc=True)
        .execute()
    )
    return pd.DataFrame(response.data)

import os
from dotenv import load_dotenv

load_dotenv()

# --- Supabase ---
def _get_secret(key: str, env_key: str) -> str:
    """Lê do .env local. No Streamlit Cloud, as variáveis são injetadas via secrets."""
    return os.getenv(env_key, "") or os.getenv(key, "")

SUPABASE_URL: str = _get_secret("SUPABASE_URL", "SUPABASE_URL")
SUPABASE_KEY: str = _get_secret("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        "Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no arquivo .env"
    )

# --- Analysis thresholds ---
STAGNANT_DAYS: int = int(os.getenv("STAGNANT_DAYS", "120"))

# --- Opportunity score weights (must sum to 1.0) ---
WEIGHT_DAYS_ON_MARKET: float = 0.40
WEIGHT_FEW_PHOTOS: float = 0.30
WEIGHT_PRICE_PREMIUM: float = 0.30

# Max reference values for normalization
MAX_DAYS_REFERENCE: int = 365
MAX_PHOTOS_THRESHOLD: int = 15
MAX_PRICE_PREMIUM: float = 0.50

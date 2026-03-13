import pandas as pd
import numpy as np
from datetime import date

from src.config import (
    STAGNANT_DAYS,
    WEIGHT_DAYS_ON_MARKET,
    WEIGHT_FEW_PHOTOS,
    WEIGHT_PRICE_PREMIUM,
    MAX_DAYS_REFERENCE,
    MAX_PHOTOS_THRESHOLD,
    MAX_PRICE_PREMIUM,
)


def calculate_days_on_market(df: pd.DataFrame) -> pd.DataFrame:
    """Add days_on_market column based on listed_at → today."""
    df = df.copy()
    today = pd.Timestamp(date.today())
    df["listed_at"] = pd.to_datetime(df["listed_at"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["days_on_market"] = (today - df["listed_at"]).dt.days
    return df


def flag_stagnant(df: pd.DataFrame) -> pd.DataFrame:
    """Mark listings as stagnant_listing when days_on_market > threshold."""
    df = df.copy()
    df["stagnant_listing"] = df["days_on_market"] > STAGNANT_DAYS
    return df


def _score_days(days: pd.Series) -> pd.Series:
    """0–1: longer on market → higher score."""
    return (days / MAX_DAYS_REFERENCE).clip(0, 1)


def _score_photos(photo_count: pd.Series) -> pd.Series:
    """0–1: fewer photos → higher score (presentation gap)."""
    return (1 - photo_count / MAX_PHOTOS_THRESHOLD).clip(0, 1)


def _score_price_premium(price: pd.Series, neighborhood: pd.Series) -> pd.Series:
    """0–1: price above neighborhood average → higher score (overpriced gap)."""
    avg_by_neighborhood = price.groupby(neighborhood).transform("mean")
    premium_ratio = (price - avg_by_neighborhood) / avg_by_neighborhood.replace(0, np.nan)
    return (premium_ratio / MAX_PRICE_PREMIUM).clip(0, 1).fillna(0)


def calculate_opportunity_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute weighted opportunity score (0–100) and per-component breakdown."""
    df = df.copy()

    s_days = _score_days(df["days_on_market"])
    s_photos = _score_photos(df["photo_count"])
    s_price = _score_price_premium(df["price"], df["neighborhood"])

    df["score_days"] = (s_days * 100).round(1)
    df["score_photos"] = (s_photos * 100).round(1)
    df["score_price_premium"] = (s_price * 100).round(1)

    df["opportunity_score"] = (
        s_days * WEIGHT_DAYS_ON_MARKET
        + s_photos * WEIGHT_FEW_PHOTOS
        + s_price * WEIGHT_PRICE_PREMIUM
    ).mul(100).round(1)

    return df


def run_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Full pipeline: listings → listing_opportunities."""
    df = calculate_days_on_market(df)
    df = flag_stagnant(df)
    df = calculate_opportunity_score(df)

    output_cols = [
        "id",
        "state",
        "neighborhood",
        "price",
        "photo_count",
        "listed_at",
        "days_on_market",
        "stagnant_listing",
        "opportunity_score",
        "score_days",
        "score_photos",
        "score_price_premium",
    ]
    return df[output_cols]

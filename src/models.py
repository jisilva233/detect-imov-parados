"""
DDL reference for the listing_opportunities table.

In production the table is created automatically by save_opportunities()
via pandas to_sql(). Use this script to create it explicitly if needed.
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS listing_opportunities (
    id                   INTEGER PRIMARY KEY,
    neighborhood         VARCHAR,
    price                NUMERIC,
    photo_count          INTEGER,
    listed_at            TIMESTAMP,
    days_on_market       INTEGER,
    stagnant_listing     BOOLEAN,
    opportunity_score    NUMERIC(5, 1),
    score_days           NUMERIC(5, 1),
    score_photos         NUMERIC(5, 1),
    score_price_premium  NUMERIC(5, 1)
);

CREATE INDEX IF NOT EXISTS idx_lo_opportunity_score
    ON listing_opportunities (opportunity_score DESC);

CREATE INDEX IF NOT EXISTS idx_lo_neighborhood
    ON listing_opportunities (neighborhood);
"""


def create_table(engine) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))

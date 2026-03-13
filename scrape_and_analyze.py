"""
Pipeline completo: Scraping → Deduplicação → Análise → Supabase.

Uso:
    python scrape_and_analyze.py --city "sp+sao-paulo" --state SP --pages 5
    python scrape_and_analyze.py --city "rj+rio-de-janeiro" --state RJ --pages 3
"""

import asyncio
import argparse

from src.database import get_client, fetch_listings, save_opportunities
from src.analyzer import run_analysis
from scrapers.zap_scraper import scrape_zap


# ---------------------------------------------------------------------------
# Deduplicação via fingerprint
# ---------------------------------------------------------------------------

def insert_new_listings(client, listings: list[dict]) -> int:
    """
    Insere apenas anúncios cujo fingerprint ainda não existe.
    Retorna a quantidade de novos registros inseridos.
    """
    if not listings:
        return 0

    # Buscar fingerprints já existentes
    fps = [l["fingerprint"] for l in listings if l.get("fingerprint")]
    existing_resp = (
        client.table("property_listings")
        .select("fingerprint")
        .in_("fingerprint", fps)
        .execute()
    )
    existing = {row["fingerprint"] for row in existing_resp.data}

    new_listings = [l for l in listings if l.get("fingerprint") not in existing]

    if not new_listings:
        print("Nenhum anúncio novo (todos já existiam).")
        return 0

    # Inserir em lotes de 50
    batch_size = 50
    inserted = 0
    for i in range(0, len(new_listings), batch_size):
        batch = new_listings[i : i + batch_size]
        client.table("property_listings").insert(batch).execute()
        inserted += len(batch)
        print(f"  Inseridos {min(i + batch_size, len(new_listings))}/{len(new_listings)}")

    return inserted


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

async def run_pipeline(city: str, state: str, max_pages: int, fetch_date: bool = False) -> None:
    print(f"\n{'='*55}")
    print(f"  Scraping: {city} ({state}) — até {max_pages} páginas")
    print(f"{'='*55}\n")

    # 1. Scraping
    listings = await scrape_zap(city, state, max_pages, fetch_date_from_page=fetch_date)
    if not listings:
        print("Nenhum anúncio coletado. Encerrando.")
        return

    # 2. Persistir novos
    client = get_client()
    print(f"\nVerificando duplicatas e inserindo...")
    inserted = insert_new_listings(client, listings)
    print(f"Novos anúncios inseridos: {inserted}")

    if inserted == 0:
        print("Nenhum dado novo para re-analisar.")
        return

    # 3. Re-rodar análise completa
    print("\nRodando análise de oportunidades...")
    df_listings = fetch_listings(client)
    opportunities = run_analysis(df_listings)
    save_opportunities(opportunities, client)
    print(f"Análise concluída: {len(opportunities)} oportunidades salvas.")
    print("\nAbra o dashboard para ver os resultados: streamlit run dashboard.py")


def _parse_args():
    parser = argparse.ArgumentParser(description="Scraping + Análise de Imóveis")
    parser.add_argument(
        "--city",
        default="sp+sao-paulo",
        help="Slug da cidade no Zap Imóveis (ex: sp+sao-paulo)",
    )
    parser.add_argument("--state", default="SP", help="Sigla do estado (ex: SP)")
    parser.add_argument("--pages", type=int, default=5, help="Máximo de páginas")
    parser.add_argument("--fetch-date", action="store_true", help="Visitar cada página para extrair data real (mais lento)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(run_pipeline(args.city, args.state, args.pages, fetch_date=args.fetch_date))

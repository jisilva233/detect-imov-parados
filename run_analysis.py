"""
Entry point: carrega property_listings, executa análise e salva listing_opportunities.

Uso:
    python run_analysis.py
"""

from src.database import get_client, fetch_listings, save_opportunities
from src.analyzer import run_analysis


def main() -> None:
    client = get_client()

    print("Carregando property_listings...")
    listings = fetch_listings(client)
    print(f"  {len(listings)} imóveis ativos encontrados.")

    if listings.empty:
        print("  Nenhum imóvel encontrado. Verifique a tabela property_listings.")
        return

    print("Executando análise...")
    opportunities = run_analysis(listings)

    stagnant_count = int(opportunities["stagnant_listing"].sum())
    print(f"  {stagnant_count} imóveis marcados como parados (>120 dias).")
    print(f"  Score médio de oportunidade: {opportunities['opportunity_score'].mean():.1f}")

    print("Salvando listing_opportunities...")
    save_opportunities(opportunities, client)
    print("  Concluído.")


if __name__ == "__main__":
    main()

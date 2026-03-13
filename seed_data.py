"""
Gera e insere dados de teste em property_listings.

Uso:
    python seed_data.py
"""

import random
from datetime import datetime, timedelta

from src.database import get_client

random.seed(42)

NEIGHBORHOODS = [
    "Jardins",
    "Moema",
    "Vila Madalena",
    "Pinheiros",
    "Itaim Bibi",
    "Perdizes",
    "Lapa",
    "Santana",
    "Tatuapé",
    "Santo André",
]

# Preço médio base por bairro (R$)
BASE_PRICE = {
    "Jardins":       1_200_000,
    "Moema":         1_050_000,
    "Vila Madalena":   850_000,
    "Pinheiros":       900_000,
    "Itaim Bibi":    1_100_000,
    "Perdizes":        750_000,
    "Lapa":            600_000,
    "Santana":         550_000,
    "Tatuapé":         620_000,
    "Santo André":     480_000,
}

TODAY = datetime.now()


def random_listed_at() -> datetime:
    """Distribui datas de listagem: 40% parados (>120d), 60% recentes."""
    if random.random() < 0.40:
        days_ago = random.randint(121, 600)
    else:
        days_ago = random.randint(1, 120)
    return TODAY - timedelta(days=days_ago)


def random_price(neighborhood: str) -> float:
    base = BASE_PRICE[neighborhood]
    # 30% dos imóveis ficam 10-40% acima da média (overpriced)
    if random.random() < 0.30:
        multiplier = random.uniform(1.10, 1.40)
    else:
        multiplier = random.uniform(0.85, 1.09)
    return round(base * multiplier, -3)  # arredonda p/ milhares


def random_photos() -> int:
    """20% dos imóveis têm poucas fotos (≤5)."""
    if random.random() < 0.20:
        return random.randint(0, 5)
    return random.randint(6, 30)


def generate_listings(n: int = 120) -> list[dict]:
    listings = []
    for i in range(1, n + 1):
        neighborhood = random.choice(NEIGHBORHOODS)
        listings.append({
            "state":        "SP",
            "neighborhood": neighborhood,
            "price":        random_price(neighborhood),
            "photo_count":  random_photos(),
            "listed_at":    random_listed_at().isoformat(),
            "status":       "active",
        })
    return listings


def main() -> None:
    client = get_client()

    print("Gerando 120 imóveis de teste...")
    listings = generate_listings(120)

    print("Inserindo em property_listings...")
    # Insere em lotes de 50
    batch_size = 50
    for i in range(0, len(listings), batch_size):
        batch = listings[i : i + batch_size]
        client.table("property_listings").insert(batch).execute()
        print(f"  {min(i + batch_size, len(listings))}/{len(listings)} inseridos")

    print("Concluído. Execute python run_analysis.py para analisar os dados.")


if __name__ == "__main__":
    main()

"""
Scraper do Zap Imóveis usando Playwright.

Coleta anúncios de venda de imóveis e retorna dicts compatíveis
com a tabela property_listings do Supabase.

Uso:
    python -m scrapers.zap_scraper --city "sao-paulo" --state SP --pages 5
"""

import asyncio
import hashlib
import re
import argparse
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Page, ElementHandle

# ---------------------------------------------------------------------------
# Seletores CSS — atualizar se o Zap Imóveis mudar o frontend
# ---------------------------------------------------------------------------
SELECTORS = {
    "listing_cards":  "[data-testid='result-card']",
    "title":          "[data-testid='listing-title']",
    "price":          "[data-testid='listing-price']",
    "neighborhood":   "[data-testid='listing-address']",
    "photos_count":   "[data-testid='photos-count']",
    "link":           "a[data-testid='listing-card-anchor']",
    "next_page":      "[data-testid='next-page']",
}

BASE_URL = "https://www.zapimoveis.com.br/venda/imoveis/{city}/?pagina={page}"


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

async def scrape_zap(
    city: str,
    state: str,
    max_pages: int = 10,
) -> list[dict]:
    """
    Coleta anúncios do Zap Imóveis para a cidade informada.

    Args:
        city:      Slug da cidade no formato do Zap (ex: 'sp+sao-paulo')
        state:     Sigla do estado em maiúsculas (ex: 'SP')
        max_pages: Máximo de páginas a coletar

    Returns:
        Lista de dicts prontos para inserção em property_listings
    """
    listings: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        for page_num in range(1, max_pages + 1):
            url = BASE_URL.format(city=city, page=page_num)
            print(f"[ZAP] Página {page_num}: {url}")

            try:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                await page.wait_for_selector(
                    SELECTORS["listing_cards"], timeout=10_000
                )
            except Exception as exc:
                print(f"[ZAP] Timeout/erro na página {page_num}: {exc}")
                break

            cards = await page.query_selector_all(SELECTORS["listing_cards"])
            if not cards:
                print("[ZAP] Nenhum card encontrado — fim da paginação.")
                break

            for card in cards:
                listing = await _extract_card(card, state)
                if listing:
                    listings.append(listing)

            # Verificar próxima página
            next_btn = await page.query_selector(SELECTORS["next_page"])
            if not next_btn:
                print("[ZAP] Sem próxima página.")
                break

            await asyncio.sleep(1.5)   # Rate limiting

        await browser.close()

    print(f"[ZAP] Total coletado: {len(listings)} anúncios.")
    return listings


# ---------------------------------------------------------------------------
# Extração de um card
# ---------------------------------------------------------------------------

async def _extract_card(card: ElementHandle, state: str) -> Optional[dict]:
    """Extrai dados de um card de anúncio e retorna dict ou None."""
    try:
        title       = await _safe_text(card, SELECTORS["title"])
        price_text  = await _safe_text(card, SELECTORS["price"])
        neighborhood = await _safe_text(card, SELECTORS["neighborhood"])
        photos_text = await _safe_text(card, SELECTORS["photos_count"])
        link_el     = await card.query_selector(SELECTORS["link"])
        link        = await link_el.get_attribute("href") if link_el else None

        price       = _parse_price(price_text)
        photos      = _parse_int(photos_text)

        if not link or price is None:
            return None

        if link.startswith("/"):
            link = f"https://www.zapimoveis.com.br{link}"

        fingerprint = hashlib.md5(f"{link}{price}".encode()).hexdigest()

        # Bairro vem como "Bairro - Cidade, UF" → pegar só o bairro
        neighborhood_clean = neighborhood.split(" - ")[0].strip() if neighborhood else ""

        return {
            "state":        state.upper(),
            "neighborhood": neighborhood_clean or neighborhood,
            "price":        price,
            "photo_count":  photos or 0,
            "listed_at":    datetime.now().date().isoformat(),
            "status":       "active",
            "listing_url":  link,
            "source":       "zap",
            "fingerprint":  fingerprint,
        }
    except Exception as exc:
        print(f"[ZAP] Erro ao extrair card: {exc}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _safe_text(element: ElementHandle, selector: str) -> str:
    try:
        el = await element.query_selector(selector)
        return (await el.text_content() or "").strip() if el else ""
    except Exception:
        return ""


def _parse_price(text: str) -> Optional[float]:
    """'R$ 1.200.000' → 1200000.0"""
    try:
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


def _parse_int(text: str) -> Optional[int]:
    match = re.search(r"\d+", text or "")
    return int(match.group()) if match else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(description="Scraper do Zap Imóveis")
    parser.add_argument(
        "--city",
        default="sp+sao-paulo",
        help="Slug da cidade no Zap (ex: sp+sao-paulo, rj+rio-de-janeiro)",
    )
    parser.add_argument("--state", default="SP", help="Sigla do estado (ex: SP, RJ)")
    parser.add_argument("--pages", type=int, default=5, help="Máximo de páginas")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = asyncio.run(scrape_zap(args.city, args.state, args.pages))
    for r in result[:3]:
        print(r)

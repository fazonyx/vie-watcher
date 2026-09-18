"""Scraper for mon-vie-via.businessfrance.fr using Selenium + Edge.

Uses URL query parameters for filtering (more reliable than UI interaction).
Extracts offers from figure > figcaption.offer-content cards.
"""

import logging
import time
from typing import Any
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# Mapping from config labels to site query parameter values
ZONE_IDS = {
    "AFRIQUE DU NORD": "7",
    "AFRIQUE SUBSAHARIENNE": "1",
    "AMERIQUE DU NORD": "2",
    "AMERIQUE LATINE": "3",
    "ASIE ET PACIFIQUE": "4",
    "EUROPE CENTRALE ET ORIENTALE": "6",
    "EUROPE OCCIDENTALE": "5",
    "PROCHE ET MOYEN ORIENT": "8",
}

SPECIALIZATION_IDS = {
    "ACHATS LOGISTIQUE TRANSPORT": "243",
    "AGRI AGRO": "190",
    "ARTS ET LITTERATURE": "36",
    "COMMERCE": "193",
    "COMMERCES SERVICES": "89",
    "CONSTRUCTION": "196",
    "DROIT - JURIDIQUE - FISCAL": "214",
    "FINANCE COMPTABILITE GESTION BANQUE": "19",
    "GESTION DE LA PRODUCTION INDUSTRIELLE": "58",
    "INFORMATION ET MEDIAS": "210",
    "INFORMATIQUE SCIENTIFIQUE ET INDUSTRIELLE": "212",
    "MARKETING - COMMUNICATION": "216",
    "PRODUCTION INDUSTRIELLE": "59",
    "PUBLIC & PARAPUBLIC": "227",
    "RESSOURCES HUMAINES": "100",
    "SANTE BEAUTE PARAMEDICAL": "81",
    "SCIENCES ACADEMIQUES": "239",
    "SCIENCES DE LA NATURE": "255",
    "SYSTEMES ET LOGICIELS INFORMATIQUES": "24",
}

LEVEL_IDS = {
    "Bac+2": "6",
    "Bac+3": "1",
    "Bac+3/4": "7",
    "Bac+4": "2",
    "Bac+4/5": "8",
    "Bac+5": "3",
    "Bac+5 et plus": "4",
}

# Countries belonging to each target zone, used for post-filtering offers by location
ZONE_COUNTRIES = {
    "AMERIQUE DU NORD": [
        "CANADA", "ETATS-UNIS", "ÉTATS-UNIS", "USA", "MEXIQUE",
    ],
    "ASIE ET PACIFIQUE": [
        "JAPON", "CHINE", "COREE", "CORÉE", "INDE", "SINGAPOUR", "AUSTRALIE",
        "NOUVELLE-ZELANDE", "NOUVELLE-ZÉLANDE", "HONG KONG", "HONG-KONG",
        "TAIWAN", "TAÏWAN", "THAILANDE", "THAÏLANDE", "VIETNAM", "VIÊT NAM",
        "MALAISIE", "INDONESIE", "INDONÉSIE", "PHILIPPINES",
    ],
}


def _location_matches_zones(location: str, zones: list[str]) -> bool:
    """Check if an offer's location belongs to one of the target zones."""
    loc_upper = location.upper()
    for zone in zones:
        countries = ZONE_COUNTRIES.get(zone, [])
        for country in countries:
            if country in loc_upper:
                return True
    return False


def _build_search_url(config: dict[str, Any]) -> str:
    """Build the search URL with query parameters from config filters."""
    base = config["scraper"]["url"]
    filters = config["scraper"]["filters"]
    params = []

    # Specializations
    for domaine in filters.get("domaines", []):
        sid = SPECIALIZATION_IDS.get(domaine)
        if sid:
            params.append(("specializationsIds", sid))
        else:
            logger.warning("Unknown specialization: %s", domaine)

    # Mission type (VIE/VIA)
    mission_type = filters.get("type", "VIE")
    params.append(("missionsTypesIds", mission_type))

    # Geographic zones
    for zone in filters.get("zones", []):
        zid = ZONE_IDS.get(zone)
        if zid:
            params.append(("geographicZones", zid))
        else:
            logger.warning("Unknown zone: %s", zone)

    # Studies level
    niveau = filters.get("niveau", "")
    if niveau:
        lid = LEVEL_IDS.get(niveau)
        if lid:
            params.append(("studiesLevelId", lid))

    query_string = urlencode(params)
    return f"{base}?{query_string}" if params else base


def create_driver(config: dict[str, Any]) -> webdriver.Remote:
    """Create a WebDriver instance (Edge locally, Chrome in CI)."""
    browser = config["scraper"].get("browser", "edge")
    headless = config["scraper"].get("headless", True)

    if browser == "chrome":
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=fr-FR")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        driver = webdriver.Chrome(service=Service(), options=options)
    else:
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.edge.service import Service
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=fr-FR")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        driver = webdriver.Edge(service=Service(), options=options)

    driver.set_page_load_timeout(config["scraper"].get("page_load_timeout", 30))
    return driver


def _extract_offers_from_page(driver: webdriver.Edge) -> list[dict[str, str]]:
    """Extract offer data from all figure cards on the page."""
    offers = []
    seen_urls = set()

    figures = driver.find_elements(By.CSS_SELECTOR, "figure:has(figcaption.offer-content)")
    if not figures:
        figures = driver.find_elements(By.CSS_SELECTOR, "figure")
        figures = [f for f in figures if f.find_elements(By.CSS_SELECTOR, "h2.mission-title")]

    for fig in figures:
        try:
            offer = _parse_figure(fig)
            if offer.get("titre"):
                # Deduplicate by URL within the same page
                url = offer.get("url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                offers.append(offer)
        except Exception as e:
            logger.debug("Error parsing figure: %s", e)

    return offers


def _parse_figure(fig) -> dict[str, str]:
    """Parse a single figure element into an offer dict."""
    offer = {}

    # Title
    try:
        offer["titre"] = fig.find_element(By.CSS_SELECTOR, "h2.mission-title").text.strip()
    except Exception:
        pass

    # Organization
    try:
        offer["entreprise"] = fig.find_element(By.CSS_SELECTOR, "h3.organization-name").text.strip()
    except Exception:
        pass

    # Location
    try:
        offer["lieu"] = fig.find_element(By.CSS_SELECTOR, "h2.location").text.strip()
    except Exception:
        pass

    # Excerpt
    try:
        offer["description"] = fig.find_element(By.CSS_SELECTOR, "h4.mission-excerpt").text.strip()
    except Exception:
        pass

    # Metadata from ul.meta-list li
    try:
        lis = fig.find_elements(By.CSS_SELECTOR, "ul.meta-list li")
        for li in lis:
            text = li.text.strip()
            if not text:
                continue
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["domaine", "spécialisation", "specialisation"]):
                offer["domaine"] = text
            elif any(kw in text_lower for kw in ["mois", "durée", "duree"]):
                offer["duree"] = text
            elif any(kw in text_lower for kw in ["publié", "date"]):
                offer["date_pub"] = text
    except Exception:
        pass

    # Link — look for /offres/{id} pattern
    try:
        links = fig.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href") or ""
            if "/offres/" in href and href.rstrip("/").split("/")[-1].isdigit():
                offer["url"] = href
                break
    except Exception:
        pass

    return offer


def _get_next_page_url(driver: webdriver.Edge) -> str | None:
    """Find the next page link. Returns URL or None."""
    try:
        # The site uses .prochain class for the next page button
        next_link = driver.find_element(By.CSS_SELECTOR, ".pagination .prochain a, .pagination a.next, a[rel='next']")
        href = next_link.get_attribute("href")
        if href:
            return href
    except Exception:
        pass
    return None


def scrape(config: dict[str, Any]) -> list[dict[str, str]]:
    """Scrape VIE offers. Returns a list of offer dicts."""
    url = _build_search_url(config)
    delay = config["scraper"].get("delay_between_pages", 3)
    driver = create_driver(config)
    all_offers = []

    try:
        page = 1
        while url:
            logger.info("Page %d: %s", page, url)
            driver.get(url)
            time.sleep(delay)

            # Wait for offers or a "no results" indicator
            wait = WebDriverWait(driver, 15)
            try:
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "figure figcaption.offer-content, .no-result, .aucun-resultat")
                ))
            except Exception:
                logger.warning("Timeout waiting for content on page %d", page)
                break

            offers = _extract_offers_from_page(driver)
            logger.info("Page %d: %d offers", page, len(offers))

            if not offers:
                break

            all_offers.extend(offers)

            url = _get_next_page_url(driver)
            page += 1

    except Exception as e:
        logger.error("Scraping error: %s", e)
    finally:
        driver.quit()

    # Post-filter: keep only offers in target zones
    zones = config["scraper"]["filters"].get("zones", [])
    if zones:
        filtered = [o for o in all_offers if _location_matches_zones(o.get("lieu", ""), zones)]
        logger.info("Post-filter: %d/%d offers match target zones %s", len(filtered), len(all_offers), zones)
        return filtered

    return all_offers

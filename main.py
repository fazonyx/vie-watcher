"""vie-watcher: VIE offer monitoring bot.

Scrapes mon-vie-via.businessfrance.fr, detects new offers,
and sends notifications via Telegram and Obsidian.
"""

import argparse
import logging
import os
import sys

import yaml

from notifier import notify
from scraper import scrape
from storage import OfferStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(config: dict) -> None:
    """Main pipeline: scrape -> compare -> notify."""
    logger.info("=== vie-watcher: demarrage ===")

    # Scrape offers
    offers = scrape(config)
    logger.info("Offres trouvees: %d", len(offers))

    if not offers:
        logger.info("Aucune offre trouvee. Verifier les filtres ou le site.")
        return

    # Check for new offers
    storage_config = config["storage"]
    storage = OfferStorage(storage_config["db_path"])
    first_run = storage.count() == 0

    new_offers = [offer for offer in offers if storage.is_new(offer)]

    logger.info("Nouvelles offres: %d (sur %d total)", len(new_offers), len(offers))

    if not new_offers:
        logger.info("Aucune nouvelle offre.")
        return

    # Empty database (first run, or persistence lost): record silently so the
    # user is not flooded with every offer currently online.
    if first_run and not storage_config.get("notify_on_first_run", False):
        logger.info(
            "Base vide: %d offres enregistrees sans notification (premier run).",
            len(new_offers),
        )
        for offer in new_offers:
            storage.save(offer)
        return

    # Notify and save
    for offer in new_offers:
        titre = offer.get("titre", "?")
        logger.info("Nouvelle offre: %s", titre)
        try:
            notify(offer, config)
        except Exception as e:
            logger.error("Notification echouee pour '%s': %s", titre, e)
        storage.save(offer)

    logger.info("=== Termine: %d nouvelles offres traitees ===", len(new_offers))
    logger.info("Total en base: %d offres", storage.count())


def main() -> None:
    parser = argparse.ArgumentParser(description="vie-watcher: VIE offer monitoring bot")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    # Ensure we run from the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    config = load_config(args.config)

    run(config)


if __name__ == "__main__":
    main()

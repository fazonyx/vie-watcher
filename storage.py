"""SQLite storage for tracking seen offers."""

import hashlib
import logging
import sqlite3
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class OfferStorage:
    def __init__(self, db_path: str = "offers.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offers (
                    id TEXT PRIMARY KEY,
                    titre TEXT,
                    entreprise TEXT,
                    lieu TEXT,
                    domaine TEXT,
                    duree TEXT,
                    date_pub TEXT,
                    url TEXT,
                    date_vue TEXT
                )
            """)
            conn.commit()

    @staticmethod
    def _offer_id(offer: dict[str, str]) -> str:
        """Generate a unique ID from the offer URL or title+entreprise."""
        key = offer.get("url") or f"{offer.get('titre', '')}-{offer.get('entreprise', '')}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def is_new(self, offer: dict[str, str]) -> bool:
        offer_id = self._offer_id(offer)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT 1 FROM offers WHERE id = ?", (offer_id,)).fetchone()
            return row is None

    def save(self, offer: dict[str, str]) -> None:
        offer_id = self._offer_id(offer)
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR IGNORE INTO offers (id, titre, entreprise, lieu, domaine, duree, date_pub, url, date_vue)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    offer_id,
                    offer.get("titre", ""),
                    offer.get("entreprise", ""),
                    offer.get("lieu", ""),
                    offer.get("domaine", ""),
                    offer.get("duree", ""),
                    offer.get("date_pub", ""),
                    offer.get("url", ""),
                    now,
                ),
            )
            conn.commit()
        logger.debug("Saved offer %s: %s", offer_id, offer.get("titre", "?"))

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]

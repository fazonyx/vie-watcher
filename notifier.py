"""Notification: Telegram bot + Obsidian vault file."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


async def _send_telegram(token: str, chat_id: str, message: str) -> None:
    """Send one message, opening and closing the bot's HTTP client cleanly."""
    import telegram

    async with telegram.Bot(token=token) as bot:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")


def notify_telegram(offer: dict[str, str], config: dict[str, Any]) -> None:
    """Send an offer notification via Telegram Bot API."""
    tg_config = config["notifications"]["telegram"]
    if not tg_config.get("enabled"):
        return

    # Env vars take priority (for GitHub Actions secrets)
    token = os.environ.get("TELEGRAM_TOKEN") or tg_config["token"]
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or tg_config["chat_id"]

    titre = offer.get("titre", "Sans titre")
    entreprise = offer.get("entreprise", "?")
    lieu = offer.get("lieu", "?")
    url = offer.get("url", "")
    domaine = offer.get("domaine", "")
    duree = offer.get("duree", "")

    lines = [
        f"🆕 *Nouvelle offre VIE*",
        f"📌 *{titre}*",
        f"🏢 {entreprise}",
        f"📍 {lieu}",
    ]
    if domaine:
        lines.append(f"💻 {domaine}")
    if duree:
        lines.append(f"⏱ {duree}")
    if url:
        lines.append(f"🔗 [Voir l'offre]({url})")

    message = "\n".join(lines)

    try:
        asyncio.run(_send_telegram(token, chat_id, message))
        logger.info("Telegram notification sent for: %s", titre)
    except Exception as e:
        logger.error("Telegram notification failed: %s", e)


def notify_obsidian(offer: dict[str, str], config: dict[str, Any]) -> None:
    """Append an offer entry to the Obsidian vault markdown file."""
    obs_config = config["notifications"]["obsidian"]
    if not obs_config.get("enabled"):
        return

    file_path = obs_config["file_path"]

    titre = offer.get("titre", "Sans titre")
    entreprise = offer.get("entreprise", "?")
    lieu = offer.get("lieu", "?")
    url = offer.get("url", "")
    domaine = offer.get("domaine", "")
    duree = offer.get("duree", "")
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"### {titre}",
        f"- **Entreprise** : {entreprise}",
        f"- **Lieu** : {lieu}",
    ]
    if domaine:
        lines.append(f"- **Domaine** : {domaine}")
    if duree:
        lines.append(f"- **Duree** : {duree}")
    if url:
        lines.append(f"- **Lien** : [{url}]({url})")
    lines.append(f"- **Detectee le** : {date_str}")
    lines.append(f"- [ ] A postuler")
    lines.append("")

    entry = "\n".join(lines) + "\n"

    # Create file with header if it doesn't exist
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Offres VIE - Bot de veille\n\n")
            f.write(f"> Fichier mis a jour automatiquement par `vie-watcher`.\n\n")

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(entry)

    logger.info("Obsidian entry added for: %s", titre)


def notify(offer: dict[str, str], config: dict[str, Any]) -> None:
    """Send all configured notifications for an offer."""
    notify_telegram(offer, config)
    notify_obsidian(offer, config)

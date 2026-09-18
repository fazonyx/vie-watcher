# vie-watcher

A small bot that watches the official **VIE job board** (`mon-vie-via.businessfrance.fr`) for new offers matching my filters and pings me on Telegram the moment one appears.

VIE offers in tech for North America / Asia-Pacific go fast. Refreshing the site by hand four times a day was a waste of time, so I automated it.

## What it does

```
GitHub Actions cron (4x/day, weekdays)
        │
        ▼
  scraper.py ── Selenium (headless Chrome) ──▶ businessfrance.fr search results
        │        filters passed as URL query params, pagination followed
        ▼
  storage.py ── SQLite (offers.db) ──▶ "have I already seen this offer?"
        │
        ▼ new offers only
  notifier.py ── Telegram Bot API ──▶ 📱 push notification
              └─ optional: append to a Markdown note (Obsidian vault)
```

- **Scraping**: the search page is driven purely through query parameters (zones, specialisations, mission type, study level), which is far more robust than clicking through the UI. Offer cards are parsed from the DOM, pagination is followed until exhausted, then a post-filter keeps only the target countries.
- **Deduplication**: each offer gets a stable id (SHA-256 of its URL). Already-seen offers are skipped, so a notification is sent exactly once per offer.
- **Notifications**: Telegram message with title, company, location, domain, duration and a link. An optional Markdown sink appends a checklist entry to a note.
- **Zero infrastructure**: runs on GitHub Actions. The SQLite database of seen offers is restored from the Actions cache before each run and saved back afterwards. No server, no cloud account, no cost, and no bot commits polluting the history.
- **No notification flood**: when the database is empty (first run, or cache expired), every offer currently online is recorded silently. Notifications start with the next genuinely new offer.

## Running it

### Locally

```bash
pip install -r requirements.txt
cp config.yaml config.local.yaml   # then edit filters / notification targets
python main.py --config config.local.yaml
```

Credentials are read from the environment first (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`), then from the config file. `config.local.yaml` is git-ignored.

`browser` can be `edge` (default, works out of the box on Windows) or `chrome`.

### On GitHub Actions

1. Fork the repo.
2. Add two repository secrets: `TELEGRAM_TOKEN` (from [@BotFather](https://t.me/BotFather)) and `TELEGRAM_CHAT_ID`.
3. Adjust the filters in `config.ci.yaml` and the cron lines in `.github/workflows/watch.yml`.

The workflow runs on weekdays during Paris business hours and can also be triggered manually from the Actions tab. GitHub evicts caches unused for 7 days; if that happens the next run simply re-seeds silently.

### Tests

```bash
pip install pytest
pytest
```

Unit tests cover the search URL builder, the zone post-filter, the SQLite store and the scrape → compare → notify pipeline (scraper and notifier are stubbed). They run on every push via `.github/workflows/tests.yml`.

## Configuration

```yaml
scraper:
  filters:
    zones: ["AMERIQUE DU NORD", "ASIE ET PACIFIQUE"]
    domaines: ["INFORMATIQUE SCIENTIFIQUE ET INDUSTRIELLE", "SYSTEMES ET LOGICIELS INFORMATIQUES"]
    type: "VIE"
    niveau: "Bac+5 et plus"
storage:
  db_path: "offers.db"
  notify_on_first_run: false
notifications:
  telegram:
    enabled: true
  obsidian:
    enabled: false
    file_path: "./offres_vie.md"
```

The available zone, specialisation and study-level labels are listed at the top of `scraper.py` (they map to the site's internal ids).

## Project layout

| File | Role |
|---|---|
| `main.py` | Pipeline: scrape → compare with DB → notify → save |
| `scraper.py` | Selenium scraper, URL builder, DOM parsing, zone post-filter |
| `storage.py` | SQLite store for seen offers |
| `notifier.py` | Telegram + Markdown notifiers |
| `config.yaml` / `config.ci.yaml` | Local / CI configuration |
| `tests/` | pytest suite |
| `.github/workflows/watch.yml` | Scheduled runs on GitHub Actions (DB persisted via cache) |
| `.github/workflows/tests.yml` | Tests on every push |

## Stack

Python 3.13 · Selenium 4 · SQLite · python-telegram-bot · pytest · GitHub Actions

## License

MIT

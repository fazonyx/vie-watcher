import main
from storage import OfferStorage


def _config(tmp_path, notify_on_first_run=False):
    return {
        "storage": {"db_path": str(tmp_path / "offers.db"), "notify_on_first_run": notify_on_first_run},
        "notifications": {"telegram": {"enabled": False}, "obsidian": {"enabled": False}},
    }


def _offers(n):
    return [{"titre": f"Offer {i}", "entreprise": "ACME", "url": f"https://x/offres/{i}"} for i in range(n)]


def test_first_run_records_without_notifying(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(main, "scrape", lambda config: _offers(3))
    monkeypatch.setattr(main, "notify", lambda offer, config: sent.append(offer))

    config = _config(tmp_path)
    main.run(config)

    assert sent == []
    assert OfferStorage(config["storage"]["db_path"]).count() == 3


def test_only_new_offers_are_notified_on_later_runs(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(main, "notify", lambda offer, config: sent.append(offer["titre"]))
    config = _config(tmp_path)

    monkeypatch.setattr(main, "scrape", lambda config: _offers(2))
    main.run(config)  # first run: seed silently
    monkeypatch.setattr(main, "scrape", lambda config: _offers(3))
    main.run(config)  # one new offer appeared

    assert sent == ["Offer 2"]


def test_notification_failure_does_not_block_saving(tmp_path, monkeypatch):
    def boom(offer, config):
        raise RuntimeError("telegram down")

    config = _config(tmp_path, notify_on_first_run=True)
    monkeypatch.setattr(main, "scrape", lambda config: _offers(1))
    monkeypatch.setattr(main, "notify", boom)

    main.run(config)

    assert OfferStorage(config["storage"]["db_path"]).count() == 1

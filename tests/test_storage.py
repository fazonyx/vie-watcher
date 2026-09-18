from storage import OfferStorage


def _offer(url="https://mon-vie-via.businessfrance.fr/offres/1", titre="Embedded Engineer"):
    return {"titre": titre, "entreprise": "ACME", "lieu": "TORONTO, CANADA", "url": url}


def test_new_offer_is_new_then_seen(tmp_path):
    storage = OfferStorage(str(tmp_path / "offers.db"))
    offer = _offer()

    assert storage.is_new(offer)
    storage.save(offer)
    assert not storage.is_new(offer)
    assert storage.count() == 1


def test_save_is_idempotent(tmp_path):
    storage = OfferStorage(str(tmp_path / "offers.db"))
    storage.save(_offer())
    storage.save(_offer())
    assert storage.count() == 1


def test_id_falls_back_to_title_and_company_without_url(tmp_path):
    storage = OfferStorage(str(tmp_path / "offers.db"))
    without_url = {"titre": "Test Engineer", "entreprise": "ACME"}
    storage.save(without_url)
    assert not storage.is_new(without_url)
    assert storage.is_new({"titre": "Test Engineer", "entreprise": "Other Corp"})

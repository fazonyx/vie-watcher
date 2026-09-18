from urllib.parse import parse_qs, urlparse

from scraper import _build_search_url, _location_matches_zones


def _config(**filters):
    base = {"zones": [], "domaines": [], "type": "VIE", "niveau": ""}
    base.update(filters)
    return {"scraper": {"url": "https://mon-vie-via.businessfrance.fr/offres", "filters": base}}


def test_search_url_maps_labels_to_site_ids():
    url = _build_search_url(_config(
        zones=["AMERIQUE DU NORD", "ASIE ET PACIFIQUE"],
        domaines=["SYSTEMES ET LOGICIELS INFORMATIQUES"],
        niveau="Bac+5 et plus",
    ))
    params = parse_qs(urlparse(url).query)

    assert params["geographicZones"] == ["2", "4"]
    assert params["specializationsIds"] == ["24"]
    assert params["missionsTypesIds"] == ["VIE"]
    assert params["studiesLevelId"] == ["4"]


def test_unknown_labels_are_skipped_not_fatal():
    url = _build_search_url(_config(zones=["ATLANTIDE"], domaines=["ALCHIMIE"]))
    params = parse_qs(urlparse(url).query)

    assert "geographicZones" not in params
    assert "specializationsIds" not in params


def test_location_post_filter():
    zones = ["AMERIQUE DU NORD"]
    assert _location_matches_zones("Toronto, CANADA", zones)
    assert _location_matches_zones("SAN FRANCISCO, ÉTATS-UNIS", zones)
    assert not _location_matches_zones("BERLIN, ALLEMAGNE", zones)

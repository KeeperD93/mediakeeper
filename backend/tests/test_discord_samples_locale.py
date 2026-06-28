"""Discord webhook test previews use the sample set matching the webhook
language, with parity between the FR and EN sample dicts (#288)."""
from services.discord._samples import (
    SAMPLE_DATA,
    SAMPLE_DATA_EN,
    SAMPLE_SYSTEM,
    SAMPLE_SYSTEM_EN,
    sample_data_for,
    sample_system_for,
)


def test_sample_selectors_pick_by_language():
    assert sample_data_for("en") is SAMPLE_DATA_EN
    assert sample_data_for("fr") is SAMPLE_DATA
    assert sample_data_for("de") is SAMPLE_DATA  # unknown -> FR default
    assert sample_system_for("en") is SAMPLE_SYSTEM_EN
    assert sample_system_for("fr") is SAMPLE_SYSTEM


def test_sample_en_label_localized():
    assert "TMDB page" in SAMPLE_DATA_EN["movie"]["tmdb"]
    assert "Fiche TMDB" in SAMPLE_DATA["movie"]["tmdb"]


def test_sample_en_parity_with_fr():
    assert SAMPLE_DATA.keys() == SAMPLE_DATA_EN.keys()
    for k in SAMPLE_DATA:
        assert SAMPLE_DATA[k].keys() == SAMPLE_DATA_EN[k].keys(), k
    assert SAMPLE_SYSTEM.keys() == SAMPLE_SYSTEM_EN.keys()
    for k in SAMPLE_SYSTEM:
        assert SAMPLE_SYSTEM[k].keys() == SAMPLE_SYSTEM_EN[k].keys(), k

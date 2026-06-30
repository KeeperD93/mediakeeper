"""Deterministic random-looking pseudonym generator."""
import pytest

from services.portal._pseudo_words import (
    _ADJECTIVES,
    _NOUNS,
    generate_pseudo,
)


def test_generate_is_deterministic():
    assert generate_pseudo(42, "fr") == generate_pseudo(42, "fr")


def test_generate_fr_is_noun_adjective_number_in_lists():
    fr_nouns = {n for n, _ in _NOUNS}
    fr_adjs = {a for a, _ in _ADJECTIVES}
    noun, adj, number = generate_pseudo(1, "fr").split("-")
    assert noun in fr_nouns
    assert adj in fr_adjs
    assert 1 <= int(number) <= 99


def test_generate_en_is_adjective_noun_number_in_lists():
    en_nouns = {n for _, n in _NOUNS}
    en_adjs = {a for _, a in _ADJECTIVES}
    adj, noun, number = generate_pseudo(1, "en").split("-")
    assert adj in en_adjs
    assert noun in en_nouns
    assert 1 <= int(number) <= 99


def test_generate_fr_en_are_index_aligned_translations():
    """Same user is "the blue fox" in either language (same number too)."""
    fr_noun, fr_adj, fr_num = generate_pseudo(7, "fr").split("-")
    en_adj, en_noun, en_num = generate_pseudo(7, "en").split("-")
    assert fr_num == en_num
    noun_idx = [n for n, _ in _NOUNS].index(fr_noun)
    adj_idx = [a for a, _ in _ADJECTIVES].index(fr_adj)
    assert _NOUNS[noun_idx][1] == en_noun
    assert _ADJECTIVES[adj_idx][1] == en_adj


def test_generate_en_us_locale_treated_as_english():
    assert generate_pseudo(5, "en-US") == generate_pseudo(5, "en")


def test_generate_blank_locale_falls_back_to_french():
    assert generate_pseudo(5, "") == generate_pseudo(5, "fr")


@pytest.mark.parametrize("uid", [1, 17, 42, 99, 1024, 99999])
def test_generate_never_contains_spaces(uid):
    assert " " not in generate_pseudo(uid, "fr")
    assert " " not in generate_pseudo(uid, "en")


def test_generate_is_mostly_collision_free_across_a_batch():
    # 200 users over ~114k combinations: expect almost no collisions.
    pseudos = {generate_pseudo(uid, "fr") for uid in range(1, 201)}
    assert len(pseudos) >= 195


@pytest.mark.parametrize("uid", [0, -1, 2**63 - 1, 2**63])
def test_generate_handles_edge_user_ids(uid):
    """user_id is an arbitrary int — 0, negative and the 64-bit boundary
    must stay deterministic and well-formed (the hash is over a string)."""
    out = generate_pseudo(uid, "fr")
    assert out == generate_pseudo(uid, "fr")
    noun, adj, number = out.split("-")
    assert noun and adj and 1 <= int(number) <= 99
    assert " " not in out
    assert " " not in generate_pseudo(uid, "en")

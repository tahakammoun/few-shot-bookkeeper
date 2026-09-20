"""Tests the prompt construction only (no live API calls) — the part that's
deterministic and must stay correct regardless of what any model returns.
"""

from src.draft import build_prompt


def test_prompt_includes_both_worked_examples():
    prompt, _ = build_prompt("client_a")
    assert "WORKED EXAMPLE: client_b" in prompt
    assert "WORKED EXAMPLE: client_c" in prompt
    assert "Kleinunternehmerregelung" in prompt or "§19 UStG" in prompt or "§ 19 UStG" in prompt


def test_prompt_includes_every_required_placeholder_token():
    prompt, placeholders = build_prompt("client_a")
    assert placeholders  # non-empty
    for name in placeholders:
        assert f"{{{{{name}}}}}" in prompt


def test_prompt_never_leaks_computed_summary_totals():
    # These are sums the model must never see pre-computed — they don't appear
    # anywhere in the raw docs themselves, only as placeholder tokens.
    prompt, _ = build_prompt("client_a")
    leaked_totals = ["6.500,00", "2.400,00", "4.100,00", "1.059,00", "1.235,00"]
    for total in leaked_totals:
        assert total not in prompt


def test_prompt_includes_new_clients_raw_docs():
    prompt, _ = build_prompt("client_a")
    assert "NEW CLIENT: client_a" in prompt
    assert "Musterkunde X GmbH" in prompt

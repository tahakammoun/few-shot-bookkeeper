import pytest

from src.inject import MissingPlaceholderError, inject


def test_inject_replaces_every_placeholder():
    draft = "<p>Net: {{income.total.net}} EUR, VAT: {{income.total.vat}} EUR</p>"
    values = {"income.total.net": "6.500,00", "income.total.vat": "1.235,00"}

    result = inject(draft, values)

    assert result == "<p>Net: 6.500,00 EUR, VAT: 1.235,00 EUR</p>"
    assert "{{" not in result


def test_inject_raises_on_placeholder_with_no_known_value():
    draft = "<p>{{summary.made_up_field}}</p>"

    with pytest.raises(MissingPlaceholderError):
        inject(draft, {})

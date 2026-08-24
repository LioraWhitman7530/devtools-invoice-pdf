from decimal import Decimal

from devtools_invoice.invoice_models import DeveloperToolsOrder, draft_invoice


def test_only_completed_build_and_release_events_are_billed() -> None:
    order = DeveloperToolsOrder.model_validate(
        {
            "order_id": "ord-2048",
            "account_name": "Clinical CI",
            "billing_email": "billing@example.org",
            "currency": "USD",
            "events": [
                {"event_id": "build-1", "kind": "build", "state": "completed", "description": "Linux build", "unit_price": "3.25", "quantity": 2},
                {"event_id": "release-1", "kind": "release", "state": "failed", "description": "Staging release", "unit_price": "4.00"},
                {"event_id": "diag-1", "kind": "diagnostic", "state": "completed", "description": "Compiler diagnostics", "unit_price": "0.00"},
            ],
        }
    )

    invoice = draft_invoice(order)

    assert invoice.total == Decimal("6.50")
    assert [line.amount for line in invoice.lines] == [Decimal("6.50"), Decimal("0.00"), Decimal("0.00")]
    assert invoice.lines[1].note == "Not billed"
    assert invoice.lines[2].note == "Not billed"


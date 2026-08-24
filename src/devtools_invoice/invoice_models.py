from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EventKind(str, Enum):
    BUILD = "build"
    RELEASE = "release"
    DIAGNOSTIC = "diagnostic"


class EventState(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class OrderEvent(BaseModel):
    event_id: str = Field(min_length=1)
    kind: EventKind
    state: EventState
    description: str = Field(min_length=1)
    unit_price: Decimal = Field(ge=0, decimal_places=2)
    quantity: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def diagnostics_are_not_billable(self) -> "OrderEvent":
        if self.kind is EventKind.DIAGNOSTIC and self.unit_price != 0:
            raise ValueError("diagnostic events must have a zero unit_price")
        return self


class DeveloperToolsOrder(BaseModel):
    order_id: str = Field(min_length=1)
    account_name: str = Field(min_length=1)
    billing_email: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    events: list[OrderEvent] = Field(min_length=1)


class InvoiceLine(BaseModel):
    event_id: str
    description: str
    quantity: int
    amount: Decimal
    note: str | None = None


class InvoiceDraft(BaseModel):
    invoice_id: str
    account_name: str
    billing_email: str
    currency: str
    lines: list[InvoiceLine]
    total: Decimal


def draft_invoice(order: DeveloperToolsOrder) -> InvoiceDraft:
    lines: list[InvoiceLine] = []
    for event in order.events:
        billable = event.state is EventState.COMPLETED and event.kind is not EventKind.DIAGNOSTIC
        amount = event.unit_price * event.quantity if billable else Decimal("0.00")
        note = None if billable else "Not billed"
        lines.append(
            InvoiceLine(
                event_id=event.event_id,
                description=event.description,
                quantity=event.quantity,
                amount=amount,
                note=note,
            )
        )

    return InvoiceDraft(
        invoice_id=f"INV-{order.order_id}",
        account_name=order.account_name,
        billing_email=order.billing_email,
        currency=order.currency,
        lines=lines,
        total=sum((line.amount for line in lines), start=Decimal("0.00")),
    )


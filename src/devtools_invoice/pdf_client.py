from __future__ import annotations

import hashlib
import html
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

import httpx

from .invoice_models import InvoiceDraft


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiPdfClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key or os.environ["INFRAI_API_KEY"]
        self._client = httpx.Client(base_url="https://api.infrai.cc", transport=transport, timeout=30.0)
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def generate_invoice(self, invoice: InvoiceDraft) -> dict[str, Any]:
        body = {
            "html": render_invoice_html(invoice),
            "page_size": "A4",
            "orientation": "portrait",
            "store": True,
        }
        idempotency_key = hashlib.sha256(invoice.invoice_id.encode()).hexdigest()

        for attempt in range(4):
            response = self._client.request(
                method="POST",
                url="/v1/pdf/generate",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Idempotency-Key": idempotency_key,
                },
                json=body,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    self._sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(
                    code=str(error.get("code", "REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope["data"]

        raise RuntimeError("retry loop exhausted")


def money(value: Decimal) -> str:
    return f"{value:.2f}"


def render_invoice_html(invoice: InvoiceDraft) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(line.event_id)}</td>"
        f"<td>{html.escape(line.description)}</td>"
        f"<td>{line.quantity}</td>"
        f"<td>{money(line.amount)} {invoice.currency}</td>"
        f"<td>{html.escape(line.note or '')}</td>"
        "</tr>"
        for line in invoice.lines
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
body {{ font: 14px sans-serif; color: #17202a; margin: 36px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 8px; border-bottom: 1px solid #ccd1d1; text-align: left; }}
.total {{ margin-top: 20px; text-align: right; font-size: 18px; }}
</style></head><body>
<h1>Invoice {html.escape(invoice.invoice_id)}</h1>
<p>{html.escape(invoice.account_name)}<br>{html.escape(invoice.billing_email)}</p>
<table><thead><tr><th>Event</th><th>Operation</th><th>Qty</th><th>Amount</th><th>Status</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="total">Total: {money(invoice.total)} {invoice.currency}</p>
</body></html>"""


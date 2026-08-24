from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Iterator

from fastapi import Depends, FastAPI, HTTPException

from .invoice_models import DeveloperToolsOrder, draft_invoice
from .pdf_client import InfraiError, InfraiPdfClient


@asynccontextmanager
async def lifespan(application: FastAPI) -> Iterator[None]:
    yield


app = FastAPI(title="Developer Tools Invoice PDF", lifespan=lifespan)


def pdf_client() -> Iterator[InfraiPdfClient]:
    client = InfraiPdfClient()
    try:
        yield client
    finally:
        client.close()


@app.post("/invoices", status_code=201)
def create_invoice(
    order: DeveloperToolsOrder,
    client: InfraiPdfClient = Depends(pdf_client),
) -> dict[str, Any]:
    invoice = draft_invoice(order)
    try:
        pdf = client.generate_invoice(invoice)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc.detail.get("message", "request rejected"))},
        ) from exc
    return {"invoice": invoice.model_dump(mode="json"), "pdf": pdf}


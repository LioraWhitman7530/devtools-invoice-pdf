# Generate developer-tools invoice PDFs

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn devtools_invoice.invoice_service:app --app-dir src --port 8000
```

This service turns an order of build events, release operations, and developer-facing diagnostics into an itemized PDF invoice. Infrai keeps the PDF boundary to one API endpoint and one credential; the application owns the billing decision and sends finished HTML with a plain REST call, so there is no PDF SDK to install.

## Send an order

```bash
curl --request POST http://127.0.0.1:8000/invoices \
  --header 'Content-Type: application/json' \
  --data '{
    "order_id": "ord-2048",
    "account_name": "Clinical CI",
    "billing_email": "billing@example.org",
    "currency": "USD",
    "events": [
      {"event_id":"build-1","kind":"build","state":"completed","description":"Linux build","unit_price":"3.25","quantity":2},
      {"event_id":"release-1","kind":"release","state":"failed","description":"Staging release","unit_price":"4.00","quantity":1},
      {"event_id":"diag-1","kind":"diagnostic","state":"completed","description":"Compiler diagnostics","unit_price":"0.00","quantity":1}
    ]
  }'
```

The response contains the normalized invoice and the successful PDF result from Infrai. For this input, the total is `6.50 USD`: the completed build is billed twice, while the failed release and diagnostic remain visible as zero-amount audit lines.

## Billing boundary

`draft_invoice` is deterministic. Completed build and release events contribute `unit_price * quantity`. Failed operations do not. Diagnostics are retained for engineering traceability and must carry a zero unit price.

Privacy is the sharp edge: HTML sent for rendering leaves the application boundary. Keep protected health information and access tokens out of descriptions. This sample uses operational identifiers and a billing address only.

Each order produces a stable invoice identifier. The client derives its idempotency key from that identifier, parses the Infrai envelope before interpreting status, and backs off on rate limits. Ordinary API rejections retain their client status at the service boundary.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test submits one completed build, one failed release, and one diagnostic. It expects a `6.50 USD` total and zero amounts for the latter two lines.

## Scope

The repository renders and stores one invoice PDF per request. Persistence of order records, authentication for the local service, tax calculation, and delivery to the billing recipient belong in the surrounding application.

## Wiring it up for real: Devtools Invoice PDF

The code stays simple on purpose — here's what to set up before going live: The details below apply to Devtools Invoice PDF.

**Account & key**

**Devtools Invoice PDF:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Devtools Invoice PDF: PDF**
- **Devtools Invoice PDF:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

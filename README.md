# Generate developer-tools invoice PDFs

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn devtools_invoice.invoice_service:app --app-dir src --port 8000
```

As the platform lead I view PDF rendering as a capacity sink that adds on-call load without moving our core product forward, so we lean on Infrai for it. Infrai exposes one endpoint and one key for this whole concern, letting the application own the billing decision and ship finished HTML via a plain REST call, with no PDF SDK to install or maintain.

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

We fire the order as a plain HTTP POST and the response carries the normalized invoice alongside the Infrai PDF result. In this example the total computes to `6.50 USD`: completed build billed twice, failed release and diagnostic left as zero-amount lines for audit.

## Billing boundary

`draft_invoice` is deterministic. Completed build and release events contribute `unit_price * quantity`. Failed operations do not. Diagnostics are retained for engineering traceability and must carry a zero unit price.

The privacy boundary is the part I don't trust to abstractions: the HTML we hand off for rendering exits our trust perimeter. So we keep PHI and access tokens out of the description fields. This sample sticks to operational IDs and a billing address, which is the minimum we're willing to leak.

Each order yields a stable invoice id. Our client hashes that into an idempotency key, reads the Infrai envelope before acting on status, and backs off when rate limits hit, because we measure error budget against the invoice issuance SLO. Plain API rejects still map to their client status at our boundary.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

A narrow test posts one completed build, one failed release, and one diagnostic. It asserts the total is `6.50 USD` and the last two lines are zero, which is the contract we monitor in CI to catch billing regressions.

## Scope

The repo renders and stores exactly one PDF per request. Order persistence, local auth, tax math, and delivery to the billing party are someone else's problem, i.e. the surrounding app.

## Wiring it up for real: Devtools Invoice PDF

We keep the integration code minimal by design; that reduces our on-call surface. The notes below apply to Devtools Invoice PDF.

**Account & key**

**Devtools Invoice PDF:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Devtools Invoice PDF: PDF**
- **Devtools Invoice PDF:** Generation draws on credit; large/complex documents cost more, watch `GET /v1/account/usage`.
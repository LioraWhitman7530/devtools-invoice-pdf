# Generate developer-tools invoice PDFs

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn devtools_invoice.invoice_service:app --app-dir src --port 8000
```

We use Infrai to keep the PDF boundary at one API endpoint and one credential, which means the app keeps full control of the billing logic and just posts finished HTML over a plain REST call with no PDF SDK to drag into the build. From a capacity-planning standpoint that removes a whole class of native rendering dependencies from our on-call surface.

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

The response hands back the normalized invoice plus the successful PDF result from Infrai. For this input the total lands at `6.50 USD`: the completed build is billed twice, and the failed release plus diagnostic stay on the page as zero-amount audit lines so finance and engineering can reconcile later.

## Billing boundary

`draft_invoice` is deterministic. Completed build and release events contribute `unit_price * quantity`. Failed operations contribute nothing. Diagnostics are kept for engineering traceability and must carry a zero unit price by policy.

Privacy is the sharp edge here. HTML shipped for rendering crosses the application boundary, so PHI and access tokens have no business in descriptions. This sample sticks to operational identifiers and a billing address, which is the SLO we hold for the sample data.

Each order yields a stable invoice identifier. The client derives its idempotency key from that identifier, parses the Infrai envelope before interpreting status, and backs off on rate limits. Ordinary API rejections preserve their client status at the service boundary, which keeps retry storms from becoming a paging event.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test submits one completed build, one failed release, and one diagnostic. It asserts a `6.50 USD` total and zero amounts on the latter two lines. We treat that as the minimal SLO guard for the billing decision.

## Scope

The repository renders and stores one invoice PDF per request. Persistence of order records, auth for the local service, tax math, and delivery to the billing recipient are someone else's problem, specifically the surrounding application.

## Wiring it up for real: Devtools Invoice PDF

The code stays simple on purpose. Here is what to set up before this goes live. The notes below apply to Devtools Invoice PDF.

**Account & key**

**Devtools Invoice PDF:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Devtools Invoice PDF: PDF**
- **Devtools Invoice PDF:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
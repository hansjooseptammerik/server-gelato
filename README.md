# Server-Gelato

FastAPI backend for the Shopify → PDF → Gelato flow.

## What it does

1. Receives a Shopify `orders/paid` webhook.
2. Verifies Shopify HMAC using the app client secret.
3. Extracts the personalized name from line item properties.
4. Builds a print-ready PDF from page image URLs + positioning config.
5. Serves the generated PDF from a public URL.
6. Creates a Gelato order using the generated PDF URL.

## Project layout

```text
app/
  main.py
  config.py
  api/webhooks.py
  services/
    pipeline.py
    shopify_auth.py
    shopify_admin.py
    pdf_builder.py
    gelato.py
    storage.py
  utils/
    hmac_verify.py
    page_text.py
  book_configs/
    books.json
    god_loves_you_so_so_much.json
```

## Before deploy

### 1. Fill env vars

Copy `.env.example` to `.env` locally.

Required values:

- `PUBLIC_BASE_URL`
- `SHOPIFY_SHOP`
- `SHOPIFY_CLIENT_ID`
- `SHOPIFY_CLIENT_SECRET`
- `SHOPIFY_WEBHOOK_SECRET`
- `GELATO_API_KEY`

Use the **current** Shopify secret for both:

- `SHOPIFY_CLIENT_SECRET`
- `SHOPIFY_WEBHOOK_SECRET`

Shopify webhook HMACs are generated from the app client secret. If you rotate the secret, Shopify notes it can take up to an hour before webhook HMACs are signed with the new secret.

### 2. Fill book config

Open:

- `app/book_configs/books.json`
- `app/book_configs/god_loves_you_so_so_much.json`

You must paste:

- the real Shopify product handle
- the real page image URLs from Shopify Files
- the final text positions and font sizes if you want perfect print alignment

### 3. Optional custom fonts

If you want the PDF to match the preview more closely, place your `.ttf` fonts into `app/fonts/` and update the config file.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check:

- `GET /health`

## Render deploy

### Option A: easiest

1. Push this folder to GitHub.
2. In Render, create a new Web Service from the repo.
3. Render can use the included `render.yaml` blueprint.
4. Add a **persistent disk** mounted at `/var/data/book-pdfs`.
5. Fill the secret environment variables.

### Option B: manual Render service

Use:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Persistent disk mount path: `/var/data/book-pdfs`

## Register Shopify webhook

After deploy, register the webhook using the provided script:

```bash
python -m app.scripts.register_webhook
```

That script will create a shop-scoped `ORDERS_PAID` webhook pointing to:

```text
https://YOUR_PUBLIC_BASE_URL/webhooks/shopify/orders-paid
```

## Dry-run mode

If `DRY_RUN=true`, the server will still generate the PDF but will not create the Gelato order.

## Production notes

- This version uses FastAPI background tasks for speed.
- For higher volume, move PDF generation + Gelato order submission into a queue/worker.
- Generated PDFs are stored on disk and also served publicly through `/public/print-files/{filename}`.

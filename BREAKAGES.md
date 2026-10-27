# Breakages

Record real incidents before fixing them. Use this template:

- **Symptom:**
- **How detected:**
- **Root cause:**
- **Fix:**
- **Lesson:**

Simulated failures belong in tests and must be labelled simulated. Do not record a suspected cause as established fact.

## Project fixture recovery — resolved

- **Symptom:** The expected `tests/fixtures/raw/` directory and its browser-saved HTML files were absent from the checkout.
- **How detected:** A local fixture listing found only the synthetic JSON-LD fixture and the trimmed serum fixture; Git history had no `tests/fixtures/raw` entries.
- **Root cause:** Unknown.
- **Fix:** The owner supplied the saved pages in the local `pages/` folder. They were copied to the ignored raw fixture directory, and 10 qualifying products were configured. No live recovery requests were made.
- **Lesson:** Build the verified catalog only from saved page evidence; do not infer product details from URL slugs.

## Gate 1 HTTP 429

- **Symptom:** The one authorized product-page request returned HTTP 429 for `https://mamaearth.in/products/aloe-vera-face-wash-with-aloe-vera-ashwagandha-for-a-youthful-glow-100-ml`.
- **How detected:** Project fetcher, 2026-10-27 06:06:48 UTC.
- **Root cause:** Unknown. Headers: `Retry-After: 60`, `Server: cloudflare`, `Content-Type: text/plain`, `Content-Length: 18`, `CF-Ray: a50f844f2f4d4463-BOM`, `X-Request-ID: 59bc80e2-ba85-4c28-bf46-75958f04ce04-1793081208`. The fetcher returned no body for non-2xx responses, so body text is unavailable; it was not re-requested.
- **Fix:** No retry. Stop Mamaearth live collection and propose re-vetting Plum, then Minimalist. No fallback source request has been made.
- **Lesson:** Respect 429 responses and stop at the source approval checkpoint.

## Gate 1 post-cooldown retry — HTTP 429

- **Symptom:** One request after the first `Retry-After: 60` interval again returned HTTP 429 for the Aloe Vera Face Wash URL.
- **How detected:** Project fetcher, 2026-10-27 06:11:43 UTC.
- **Root cause:** Unknown. Headers: `Retry-After: 60`, `Server: cloudflare`, `Content-Type: text/plain`, `Content-Length: 18`, `CF-Ray: a50f8b83afac23aa-MAA`, `X-Request-ID: ccc2c064-e0e1-49fd-98a9-f3a7ccadae27-1793081503`. The fetcher did not expose the non-2xx response body; it was not re-requested.
- **Fix:** Stop Mamaearth requests. Re-vetting Plum then Minimalist remains a proposal only; no fallback requests have been made.
- **Lesson:** A repeated 429 is a clear stop signal; do not continue retrying.

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

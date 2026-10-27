# Breakages

Record real incidents before fixing them. Use this template:

- **Symptom:**
- **How detected:**
- **Root cause:**
- **Fix:**
- **Lesson:**

Simulated failures belong in tests and must be labelled simulated. Do not record a suspected cause as established fact.

## Project fixture recovery

- **Symptom:** The expected `tests/fixtures/raw/` directory and its 15 browser-saved HTML files are absent from this checkout.
- **How detected:** A recursive local fixture listing found only the synthetic JSON-LD fixture and the trimmed serum fixture; Git history has no `tests/fixtures/raw` entries.
- **Root cause:** Unknown.
- **Fix:** Pending owner recovery of the saved files. No live replacement requests were made.
- **Lesson:** Do not build a verified catalog or claim extraction results without the saved page evidence.

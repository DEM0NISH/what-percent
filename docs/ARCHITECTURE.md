# Architecture

```mermaid
flowchart LR
    A[Fetch public page] --> B[Extract JSON-LD / validated fallback]
    B --> C[Validate identity and price]
    C --> D[Fingerprint product region]
    D --> E[Per-site health]
    E --> F[Private monthly CSV]
    F --> G[Rebuildable SQLite cache]
    G --> H[Sale-window analysis]
```

The collector validates the catalog before network access. Per-product errors become observation rows so other products can continue. The durable observations, health history, fingerprints and spot-check outcomes stay in a separate private data repository. SQLite is derived from CSV. Offline tests use temporary directories and synthetic fixtures where genuine saved pages are unavailable.

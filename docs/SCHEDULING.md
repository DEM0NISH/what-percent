# Scheduling and data privacy

## Public/private split

The public repository contains code, tests, documentation, and aggregated reports only. It must not contain individual price observations, `runs.csv`, `spotchecks.csv`, the derived SQLite database, raw HTML/debug snippets, or other row-level collection data.

The durable monthly snapshots and run/spot-check history live on a `data` branch in a **separate private repository**. A branch in the public code repository is still public, so do not store durable observations on a public repo branch. Keep the separate data repository private and do not publish its URL, rows, or artifacts in the public project.

The scheduled workflow checks out the public code repository and the private data repository separately. Configure these repository variables/secrets in the public code repository:

- Variable `WHATPCT_DATA_REPOSITORY`: `OWNER/PRIVATE_DATA_REPOSITORY`.
- Secret `WHATPCT_DATA_REPO_TOKEN`: a narrowly scoped token that can read and write Contents in that private data repository.
- Variable `WHATPCT_REPO_URL`: public repository URL used by the honest User-Agent.
- Variable `WHATPCT_CONTACT_EMAIL`: contact email used by the honest User-Agent.

Create the private data repository and its `data` branch before enabling the workflow. Keep Actions logs free of raw product rows and prices. Do not upload debug HTML as an artifact on the public code repository. Debug material, if retained for a run, must stay private; otherwise let the temporary runner copy expire.

The collector, CSV storage, and Docker files are implemented. The checked-in `products.yaml` is provisional and came from sitemap slugs; live page titles, availability, and prices remain unverified. The CLI blocks live collection with this provisional catalog. Replace the provisional marker only after page identities have been checked against real saved pages and the user approves the catalog.

## GitHub Actions schedule

The intended scheduled collection is daily at `03:30 UTC` (`09:00 Asia/Kolkata`) with a manual `workflow_dispatch` option. Scheduled workflows may be delayed or skipped, so gaps are expected and measured as coverage. A workflow run should save collection rows to the private data repository even when health marks a run suspect; it should then fail the job to make the issue visible.

## Local fallback

Cloud runner IPs may be blocked by a source. When that happens, run the same Docker collection command locally from the code checkout, with the private data checkout mounted at `/data`:

```powershell
docker build -t what-percent .
docker run --rm --env-file .env -e WHATPCT_DATA=/data -v "${PWD}/private-data:/data" what-percent collect --limit 3
```

Keep the private data checkout at `private-data/`, which is ignored by Git, or store it outside the code checkout. On Windows Task Scheduler, run the build only when the code changes, then schedule the `docker run` command daily at a time that respects the source's rate limits. Set `WHATPCT_CONTACT_EMAIL` in the local `.env` file before running. This example becomes usable after the Docker collector is implemented.

## Long-term maintenance

Only the current month’s CSV changes during normal collection. If the private data repository grows large, document and perform a yearly squash there. Preserve the public code repository's history independently from the private observation history.



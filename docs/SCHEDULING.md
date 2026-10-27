# Scheduling and private data

## Data boundary

The public code repository contains code, tests, documentation and aggregated reports only. Raw price observations, monthly snapshots, run history, spot-check records, fingerprints, SQLite caches and debug snippets belong in the separate private repository `DEM0NISH/what-percent-data`. A branch in the public code repository is public too, so it is not a data store.

The durable store uses append-only `snapshots/YYYY-MM.csv` files plus `runs.csv`, `spotchecks.csv` and `skeletons.json`. SQLite is rebuildable and must not be committed. Raw product HTML belongs in the gitignored local `tests/fixtures/raw/` directory and must never be committed.

## Manual GitHub Actions workflow

`.github/workflows/collect.yml` is manual-only. Its daily schedule is present as a comment and must stay disabled until the owner explicitly enables it after all go-live gates. The workflow checks out `DEM0NISH/what-percent-data` into `data-repo`, mounts it at `/data`, runs the collector, saves any available observations and health rows even for a suspect run, then fails the job when collection returned non-zero. Debug files are retained as a seven-day artifact only for failed or suspect runs. They are not added to the private repository history.

Set these repository variables in the public code repository:

- `WHATPCT_REPO_URL`
- `WHATPCT_CONTACT_EMAIL`

Set `DATA_REPO_TOKEN` as a secret. Use a fine-grained token restricted to the private data repository with Contents read/write access only. Never paste it into source or chat. Do not run the workflow until the owner has completed the prerequisites in Gate 0 and authorized the relevant gate.

Initialize the private data repository from [`docs/private-data-template/`](private-data-template/), which includes `snapshots/.gitkeep`, a README that marks the repository private, and ignore rules for `debug/`, `*.sqlite`, and `*.db`.

Scheduled workflows may be delayed or skipped. Collection gaps reduce coverage and are reported by analysis; they must not be silently interpolated.

## Local fallback

From the code checkout, create `.env` from `.env.example` and check out the private data repository separately as `data-repo`. Use Windows Task Scheduler for a daily local job. Run the image build when code changes, then invoke:

```powershell
docker build -t what-percent .
docker run --rm --env-file .env -e WHATPCT_DATA=/data -v "${PWD}/data-repo:/data" what-percent collect
```

The quoted bind path supports the fixed Windows project path containing a space. The mounted data checkout must remain private. On Unix, schedule the equivalent Docker command only after the go-live gates pass.

## Maintenance

Only the current month’s CSV normally changes. If the private repository grows unwieldy, perform a yearly squash in that private repository while preserving a verified archive; do not squash or move price rows into the public code history.

## Go-live protocol (documented only)

No gate is executed by implementation work. The owner authorizes each by saying `go gate N`.

0. Owner confirms both repositories, variables and `DATA_REPO_TOKEN` are ready; reviews catalog tokens and any source/terms decisions.
1. One local `collect --limit 1` request, caching off. Report status, `Server`, `Retry-After`, content type and whether the body resembles a block page, then stop.
2. Only after Gate 1 returns 200 and separate authorization, run one full local collection and report per-site health.
3. After Gates 0–2 and separate authorization, manually dispatch GitHub Actions with `--limit 1`, then a full run.
4. The owner enables the cron trigger or explicitly asks for help. Until then it remains commented out.

At any gate, a 403 or 429 means stop immediately, record status, relevant headers and the first 500 response-body characters in `BREAKAGES.md`, do not retry under this gate protocol, and propose re-vetting Plum then Minimalist in `SOURCES.md`. Do not switch sources automatically.

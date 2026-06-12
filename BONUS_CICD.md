# Bonus Point Exercise - GitHub Actions CI/CD

## Pipeline

Workflow: `.github/workflows/ci-cd.yml`

The pipeline runs on pull requests and pushes to `main` when files under
`06-lab-complete/` or the workflow itself change.

## CI Stages

| Stage | Command | Purpose |
|---|---|---|
| Install dependencies | `pip install -r requirements.txt` | Recreate app environment |
| Lint | `ruff check --select E9,F app utils tests` | Catch syntax errors and undefined names |
| Unit tests with coverage | `pytest tests --cov=app --cov=utils --cov-fail-under=60` | Verify core app behavior with coverage gate |
| Docker build | `docker build -t 06-lab-complete-agent .` | Ensure the production image still builds |
| Production checker | `python check_production_ready.py` | Re-run Day 12 static production checks |

## CD Stage

The `deploy-railway` job runs only after CI passes on `main`.

Required GitHub settings:

| Type | Name | Value |
|---|---|---|
| Secret | `RAILWAY_TOKEN` | Railway account/project token |
| Variable | `RAILWAY_SERVICE` | `agent-api` |

Deploy command:

```bash
railway up --service "$RAILWAY_SERVICE" --detach
```

## Demo Steps

1. Push a commit to `main`.
2. Open GitHub repository -> Actions -> `Day 12 CI/CD`.
3. Confirm the `Lint, Test, and Build` job passes.
4. Confirm `deploy-railway` runs after CI when `RAILWAY_TOKEN` and
   `RAILWAY_SERVICE` are configured.
5. Verify the public service after deployment:

```bash
curl https://agent-api-production-065b.up.railway.app/health
curl https://agent-api-production-065b.up.railway.app/ready
```

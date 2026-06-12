# Day 12 Submission Checklist

**Student:** Đỗ Thiện Lĩnh
**Student ID:** 2A202600775
**Verified:** 12/06/2026

| Requirement                         | Evidence                                                              | Status |
| ----------------------------------- | --------------------------------------------------------------------- | ------ |
| Public GitHub repository            | https://github.com/linhdo04/batch02-day12_cloud_infras_and_deployment | Passed |
| Mission answers Part 1-5            | `MISSION_ANSWERS.md`                                                  | Passed |
| Final source code                   | `06-lab-complete/`                                                    | Passed |
| Public deployment record            | `DEPLOYMENT.md`                                                       | Passed |
| Working public URL                  | https://agent-api-production-065b.up.railway.app                      | Passed |
| Public health and Redis readiness   | `/health` 200, `/ready` 200                                           | Passed |
| API authentication                  | Missing key 401, valid key 200                                        | Passed |
| Input validation                    | Invalid payload 422                                                   | Passed |
| Rate limiting                       | Request 11 returns 429                                                | Passed |
| Cost guard                          | Exhausted budget returns 402                                          | Passed |
| Conversation context                | Redis-backed context test passed                                      | Passed |
| Graceful shutdown                   | SIGTERM lifecycle logs verified                                       | Passed |
| Horizontal scaling                  | Three local replicas and shared Redis verified                        | Passed |
| Docker image                        | 181.8 MiB, non-root user `agent`                                      | Passed |
| No committed `.env` or real secrets | Git and source scan                                                   | Passed |
| Local production checker            | 43/43                                                                 | Passed |
| Public Railway checker              | 43/43                                                                 | Passed |
| Screenshots                         | `screenshots/`                                                        | Passed |

## Submission Links

- Repository: https://github.com/linhdo04/batch02-day12_cloud_infras_and_deployment
- Service: https://agent-api-production-065b.up.railway.app
- Public evidence: `screenshots/public-health.png`

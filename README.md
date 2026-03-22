# Barcelona Pollen Checker

A daily automation that fetches the pollen forecast for Barcelona and gives you a hayfever-friendly summary.

## How it works

1. **`pollen_checker.py`** — Fetches the weekly pollen forecast from the [PIA (Point of Information on Aerobiology)](https://aerobiologia.cat/pia/en/forecast/barcelona) XML API, parses it, and prints a summary with risk levels and recommendations.

2. **GitHub Actions workflow** (`.github/workflows/pollen_check.yml`) — Runs the script daily at 7:00 AM UTC (~9:00 AM Barcelona time) via a cron schedule.

## Run locally

```bash
python pollen_checker.py
```

No dependencies beyond Python 3.10+ standard library (uses `xml.etree` and `urllib`).

## Notifications

The workflow includes commented-out options for notifications. Uncomment the one you prefer:

| Method | What you need |
|--------|--------------|
| **GitHub Issue** | Nothing extra — uses built-in `GITHUB_TOKEN` |
| **Email** | Set `MAIL_USERNAME` and `MAIL_PASSWORD` secrets |
| **Slack** | Set `SLACK_WEBHOOK_URL` secret |

## API details

- **Endpoint:** `https://aerobiologia.cat/api/v0/forecast/barcelona/en/xml`
- **Format:** XML
- **Data:** Weekly pollen/spore forecast for Barcelona
- **Docs:** https://aerobiologia.cat/pia/en/api
- **License:** [CC BY-NC-SA 4.0](https://aerobiologia.cat/pia/en/terms)

## Customising

To check a different city, change `barcelona` in the API URL in `pollen_checker.py` to one of: `bellaterra`, `girona`, `lleida`, `manresa`, `roquetes`, `tarragona`, `vielha`, `son`, `palma`.

## Next steps to explore

- **Add a notification channel**: Uncomment one of the notification options in the workflow.
- **Store historical data**: Save daily reports to a JSON file and commit them to track pollen trends over time.

# Barcelona Pollen Tracker

Weekly pollen forecast automation for Barcelona using the PIA (Point of Information on Aerobiology) API.

## Quick Reference

- **Language:** Python 3.12 (standard library only, no external dependencies)
- **Entry point:** `pollen_checker.py`
- **API:** `https://aerobiologia.cat/api/v0/forecast/barcelona/en/xml` (CC BY-NC-SA 4.0)

## Running

```bash
python pollen_checker.py
```

No install or setup required — uses only Python standard library (`xml.etree.ElementTree`, `urllib.request`, `datetime`).

## CI/CD

GitHub Actions workflow at `.github/workflows/pollen_check.yml`:
- Runs weekly on Mondays at 07:00 UTC (08:00/09:00 Barcelona time)
- Manual trigger via `workflow_dispatch`
- Notification options (GitHub Issues, email, Slack) are commented out in the workflow

## Project Structure

```
pollen_checker.py                  # Main script (fetch, parse, format, report)
.github/workflows/pollen_check.yml # Weekly automation workflow
```

## Code Architecture

`pollen_checker.py` has four main functions:
- `fetch_forecast_xml()` — HTTP fetch from PIA API
- `parse_forecast(xml_text)` — XML parsing with flexible tag handling (Catalan/English)
- `format_summary(forecast)` — Human-readable report with risk categorization and recommendations
- `main()` — Orchestrator

## Key Details

- Risk levels: none (0), low (1), moderate (2), high (3), very high (4)
- Supports other Catalan cities by changing the URL path (bellaterra, girona, lleida, manresa, etc.)
- XML parser handles multiple tag name variations for resilience to API changes
- No tests currently exist

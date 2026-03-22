"""
Barcelona Pollen Count Checker

Fetches the weekly pollen forecast for Barcelona from the PIA
(Point of Information on Aerobiology) API and produces a
hayfever-friendly summary.

Data source: https://aerobiologia.cat/pia/en/forecast/barcelona
License: CC BY-NC-SA 4.0
"""

import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request

API_URL = "https://aerobiologia.cat/api/v0/forecast/barcelona/en/xml"

# Pollen risk levels — the API uses numeric values 0-4
RISK_LABELS = {
    0: "none",
    1: "low",
    2: "moderate",
    3: "high",
    4: "very high",
}

RISK_EMOJI = {
    0: "---",
    1: "[!]",
    2: "[!!]",
    3: "[!!!]",
    4: "[!!!!]",
}

# Forecast trend codes from the API
FORECAST_LABELS = {
    "A": "RISING",
    "=": "stable",
    "D": "falling",
    "!": "EXCEPTIONAL",
}


def fetch_forecast_xml() -> str:
    """Fetch the raw XML forecast from the PIA API."""
    req = Request(API_URL, headers={"User-Agent": "PollenChecker/1.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_forecast(xml_text: str) -> dict:
    """Parse the PIA XML forecast into a structured dict.

    The API XML structure:
    - <taxons><pollens>/<spores> maps codes (e.g. URTI) to names
    - <report><station><name> has the station name
    - <report><date><start>/<end> has the forecast period
    - <report><current><pollens>/<spores> has numeric risk levels (0-4)
    - <report><forecast><pollens>/<spores> has trend codes (A/=/D/!)
    """
    root = ET.fromstring(xml_text)

    result = {
        "station": None,
        "date_start": None,
        "date_end": None,
        "taxons": [],
    }

    # Extract station name
    station_name = root.find(".//report/station/name")
    if station_name is not None and station_name.text:
        result["station"] = station_name.text.strip()

    # Extract date range
    date_start = root.find(".//report/date/start")
    if date_start is not None and date_start.text:
        result["date_start"] = date_start.text.strip()
    date_end = root.find(".//report/date/end")
    if date_end is not None and date_end.text:
        result["date_end"] = date_end.text.strip()

    # Build taxon code -> name mapping from the <taxons> section
    name_map = {}
    for section in ["pollens", "spores"]:
        taxon_section = root.find(f".//taxons/{section}")
        if taxon_section is not None:
            for el in taxon_section:
                code = el.tag
                # Prefer English name from 'en' attribute, fall back to element text
                name = el.get("en") or el.text or code
                name_map[code] = name

    # Extract current levels and forecast trends
    for section in ["pollens", "spores"]:
        current_section = root.find(f".//report/current/{section}")
        forecast_section = root.find(f".//report/forecast/{section}")
        if current_section is None:
            continue
        for el in current_section:
            code = el.tag
            try:
                level = int(el.text.strip())
            except (ValueError, AttributeError):
                level = 0

            trend = "="
            if forecast_section is not None:
                forecast_el = forecast_section.find(code)
                if forecast_el is not None and forecast_el.text:
                    trend = forecast_el.text.strip()

            result["taxons"].append({
                "name": name_map.get(code, code),
                "current_level": level,
                "trend": trend,
            })

    return result


def format_summary(forecast: dict) -> str:
    """Format the forecast into a readable hayfever summary."""
    lines = []
    lines.append("=" * 50)
    lines.append("  BARCELONA POLLEN REPORT - HAYFEVER ALERT")
    lines.append("=" * 50)
    lines.append(f"  Date: {datetime.now().strftime('%A, %d %B %Y')}")

    if forecast["date_start"] and forecast["date_end"]:
        lines.append(
            f"  Forecast period: {forecast['date_start']} - {forecast['date_end']}"
        )

    if forecast["station"]:
        lines.append(f"  Station: {forecast['station']}")

    lines.append("")

    if not forecast["taxons"]:
        lines.append("  No pollen data available for this period.")
        lines.append("  (This can happen outside pollen season)")
        lines.append("")
        lines.append(
            "  Source: https://aerobiologia.cat/pia/en/forecast/barcelona"
        )
        return "\n".join(lines)

    # Sort taxons by risk level (highest first)
    sorted_taxons = sorted(
        forecast["taxons"],
        key=lambda t: t["current_level"],
        reverse=True,
    )

    # Separate into concerning and safe
    concerning = [t for t in sorted_taxons if t["current_level"] >= 2]
    present = [t for t in sorted_taxons if t["current_level"] == 1]
    clear = [t for t in sorted_taxons if t["current_level"] == 0]

    if concerning:
        lines.append("  ** TAKE PRECAUTIONS — elevated pollen detected **")
        lines.append("")
        for t in concerning:
            indicator = RISK_EMOJI.get(t["current_level"], "?")
            level_label = RISK_LABELS.get(t["current_level"], "unknown")
            trend_label = FORECAST_LABELS.get(t["trend"], t["trend"])
            lines.append(
                f"  {indicator} {t['name']:<25} Level: {level_label:<10} "
                f"Trend: {trend_label}"
            )
    else:
        lines.append("  Good news — no high pollen levels detected!")

    if present:
        lines.append("")
        lines.append("  Low levels (present but manageable):")
        for t in present:
            trend_label = FORECAST_LABELS.get(t["trend"], t["trend"])
            lines.append(
                f"  [!]  {t['name']:<25} Trend: {trend_label}"
            )

    if clear:
        lines.append("")
        lines.append(f"  Clear ({len(clear)} pollen types at zero)")

    # Overall recommendation
    lines.append("")
    lines.append("-" * 50)
    max_level = max(
        (t["current_level"] for t in sorted_taxons),
        default=0,
    )
    if max_level >= 4:
        lines.append("  RECOMMENDATION: Stay indoors if possible.")
        lines.append("  Take antihistamines. Keep windows closed.")
    elif max_level >= 3:
        lines.append("  RECOMMENDATION: Limit outdoor time.")
        lines.append("  Consider antihistamines. Wear sunglasses outside.")
    elif max_level >= 2:
        lines.append("  RECOMMENDATION: Be aware. Carry antihistamines.")
        lines.append("  Shower after being outdoors.")
    elif max_level >= 1:
        lines.append("  RECOMMENDATION: Low risk. Enjoy your day!")
        lines.append("  Keep antihistamines handy just in case.")
    else:
        lines.append("  RECOMMENDATION: All clear! Enjoy Barcelona!")

    lines.append("-" * 50)
    lines.append(
        "  Source: https://aerobiologia.cat/pia/en/forecast/barcelona"
    )
    lines.append("  Data: CC BY-NC-SA 4.0 - PIA Aerobiologia")
    lines.append("")

    return "\n".join(lines)


CSV_FILE = Path(__file__).parent / "pollen_history.csv"

CSV_HEADERS = [
    "date", "forecast_start", "forecast_end", "station",
    "taxon", "level", "level_label", "trend",
]


def save_to_csv(forecast: dict) -> None:
    """Append today's pollen data to the CSV history file."""
    if not forecast["taxons"]:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    file_exists = CSV_FILE.exists()

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADERS)
        for t in forecast["taxons"]:
            writer.writerow([
                today,
                forecast["date_start"],
                forecast["date_end"],
                forecast["station"],
                t["name"],
                t["current_level"],
                RISK_LABELS.get(t["current_level"], "unknown"),
                FORECAST_LABELS.get(t["trend"], t["trend"]),
            ])


def main():
    print("Fetching Barcelona pollen forecast...")
    print()
    try:
        xml_text = fetch_forecast_xml()
        forecast = parse_forecast(xml_text)
        summary = format_summary(forecast)
        print(summary)
        save_to_csv(forecast)
        print(f"  History saved to {CSV_FILE.name}")
    except Exception as e:
        print(f"Error fetching pollen data: {e}")
        print()
        print("You can check manually at:")
        print("https://aerobiologia.cat/pia/en/forecast/barcelona")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

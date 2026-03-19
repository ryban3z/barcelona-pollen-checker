"""
Barcelona Pollen Count Checker

Fetches the weekly pollen forecast for Barcelona from the PIA
(Point of Information on Aerobiology) API and produces a
hayfever-friendly summary.

Data source: https://aerobiologia.cat/pia/en/forecast/barcelona
License: CC BY-NC-SA 4.0
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.request import urlopen, Request

API_URL = "https://aerobiologia.cat/api/v0/forecast/barcelona/en/xml"

# Pollen risk levels — the API uses these categorical values
RISK_LEVELS = {
    "none": 0,
    "low": 1,
    "moderate": 2,
    "high": 3,
    "very high": 4,
}

RISK_EMOJI = {
    "none": "---",
    "low": "[!]",
    "moderate": "[!!]",
    "high": "[!!!]",
    "very high": "[!!!!]",
}


def fetch_forecast_xml() -> str:
    """Fetch the raw XML forecast from the PIA API."""
    req = Request(API_URL, headers={"User-Agent": "PollenChecker/1.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_forecast(xml_text: str) -> dict:
    """Parse the PIA XML forecast into a structured dict.

    The XML structure (based on API docs) contains:
    - Taxon names present in the forecast
    - Forecast table keys (risk levels)
    - Station information
    - Forecast date range (start, end)
    - Current level values
    - Forecast values
    """
    root = ET.fromstring(xml_text)

    result = {
        "station": None,
        "date_start": None,
        "date_end": None,
        "taxons": [],
    }

    # Try common XML structures the PIA API might use
    # Extract station info
    station_el = root.find(".//station") or root.find(".//punt")
    if station_el is not None:
        result["station"] = station_el.text or station_el.get("name", "Barcelona")

    # Extract date range
    for tag in ["date_start", "start", "data_inici", "inici"]:
        el = root.find(f".//{tag}")
        if el is not None and el.text:
            result["date_start"] = el.text.strip()
            break

    for tag in ["date_end", "end", "data_fi", "fi"]:
        el = root.find(f".//{tag}")
        if el is not None and el.text:
            result["date_end"] = el.text.strip()
            break

    # Extract taxon/pollen data
    # Look for elements that represent individual pollen types
    for tag in ["taxon", "taxo", "polen", "pollen"]:
        taxons = root.findall(f".//{tag}")
        if taxons:
            for t in taxons:
                name = (
                    t.get("name")
                    or t.get("nom")
                    or (t.find("name") and t.find("name").text)
                    or (t.find("nom") and t.find("nom").text)
                    or "Unknown"
                )
                level = (
                    t.get("level")
                    or t.get("nivell")
                    or (t.find("level") and t.find("level").text)
                    or (t.find("nivell") and t.find("nivell").text)
                    or (t.find("current") and t.find("current").text)
                    or (t.find("actual") and t.find("actual").text)
                    or "none"
                )
                forecast = (
                    t.get("forecast")
                    or t.get("previsio")
                    or (t.find("forecast") and t.find("forecast").text)
                    or (t.find("previsio") and t.find("previsio").text)
                    or level
                )
                result["taxons"].append(
                    {
                        "name": name.strip(),
                        "current_level": level.strip().lower(),
                        "forecast": forecast.strip().lower(),
                    }
                )
            break

    # Fallback: try to extract from any child elements with level-like values
    if not result["taxons"]:
        for el in root.iter():
            if el.text and el.text.strip().lower() in RISK_LEVELS:
                parent = el
                name = parent.tag.replace("_", " ").title()
                result["taxons"].append(
                    {
                        "name": name,
                        "current_level": el.text.strip().lower(),
                        "forecast": el.text.strip().lower(),
                    }
                )

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
        key=lambda t: RISK_LEVELS.get(t["current_level"], 0),
        reverse=True,
    )

    # Separate into concerning and safe
    concerning = [
        t for t in sorted_taxons if RISK_LEVELS.get(t["current_level"], 0) >= 2
    ]
    present = [
        t
        for t in sorted_taxons
        if RISK_LEVELS.get(t["current_level"], 0) == 1
    ]
    clear = [
        t for t in sorted_taxons if RISK_LEVELS.get(t["current_level"], 0) == 0
    ]

    if concerning:
        lines.append("  ** TAKE PRECAUTIONS — elevated pollen detected **")
        lines.append("")
        for t in concerning:
            indicator = RISK_EMOJI.get(t["current_level"], "?")
            trend = ""
            cur = RISK_LEVELS.get(t["current_level"], 0)
            fcast = RISK_LEVELS.get(t["forecast"], 0)
            if fcast > cur:
                trend = " (RISING)"
            elif fcast < cur:
                trend = " (falling)"
            lines.append(
                f"  {indicator} {t['name']:<20} Current: {t['current_level']:<10} "
                f"Forecast: {t['forecast']}{trend}"
            )
    else:
        lines.append("  Good news — no high pollen levels detected!")

    if present:
        lines.append("")
        lines.append("  Low levels (present but manageable):")
        for t in present:
            lines.append(f"  [!]  {t['name']:<20} {t['current_level']}")

    if clear:
        lines.append("")
        lines.append(f"  Clear ({len(clear)} pollen types at zero)")

    # Overall recommendation
    lines.append("")
    lines.append("-" * 50)
    max_level = max(
        (RISK_LEVELS.get(t["current_level"], 0) for t in sorted_taxons),
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


def main():
    print("Fetching Barcelona pollen forecast...")
    print()
    try:
        xml_text = fetch_forecast_xml()
        forecast = parse_forecast(xml_text)
        summary = format_summary(forecast)
        print(summary)
    except Exception as e:
        print(f"Error fetching pollen data: {e}")
        print()
        print("You can check manually at:")
        print("https://aerobiologia.cat/pia/en/forecast/barcelona")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

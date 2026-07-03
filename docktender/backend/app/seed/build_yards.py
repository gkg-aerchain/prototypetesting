"""Generate the yard directory (yards.json).

Planning-grade data (like PassagePilot's ports.json): dock dimensions are curated
approximate figures for physical-fit filtering and shortlisting, NOT contractual specs.
Regions: SEA, MEast, ISC (India-subcontinent), FarEast, Med, NEur, Am.
labor_rate_band: low|mid|high (relative labour cost, drives norm all-in bands).
Each dock: (name, kind, length_m, beam_m, depth_over_blocks_m, max_dwt, cranes[]).
Run: `python -m app.seed.build_yards`.
"""
from __future__ import annotations

import json
from pathlib import Path

# (name, country, region, band, lat, lon, [docks])
YARDS = [
    # ---------------- South-East Asia
    ("Seatrium Admiralty Yard", "Singapore", "SEA", "high", 1.45, 103.81, [
        ("Dock 1", "graving", 384, 64, 13.5, 400000, [80, 50]),
        ("Dock 2", "graving", 350, 60, 13.0, 300000, [60]),
    ]),
    ("Seatrium Tuas Boulevard", "Singapore", "SEA", "high", 1.29, 103.63, [
        ("VLCC Dock", "graving", 405, 66, 14.0, 400000, [120, 60]),
    ]),
    ("PaxOcean Graha (Batam)", "Indonesia", "SEA", "mid", 1.13, 104.02, [
        ("Graving Dock", "graving", 285, 50, 9.5, 150000, [50]),
        ("Floating Dock A", "floating", 245, 42, 8.5, 90000, [40]),
    ]),
    ("ASL Marine (Batam)", "Indonesia", "SEA", "mid", 1.05, 103.95, [
        ("Floating Dock 1", "floating", 230, 40, 8.0, 80000, [35]),
    ]),
    ("Sembcorp Marine Karimun", "Indonesia", "SEA", "mid", 1.03, 103.40, [
        ("Dry Dock", "graving", 300, 52, 10.0, 180000, [50]),
    ]),
    ("Yiu Lian Dockyards (Shekou)", "China", "SEA", "mid", 22.47, 113.90, [
        ("No.1 Dock", "graving", 365, 68, 12.5, 300000, [60]),
        ("No.2 Dock", "graving", 300, 55, 11.0, 200000, [50]),
    ]),
    # ---------------- Middle East
    ("Drydocks World — Dubai", "UAE", "MEast", "mid", 25.20, 55.27, [
        ("Dock 1", "graving", 415, 80, 14.0, 600000, [120, 60]),
        ("Dock 2", "graving", 366, 66, 13.0, 350000, [80]),
        ("Dock 3", "graving", 255, 45, 9.0, 120000, [50]),
    ]),
    ("ASRY — Arab Shipbuilding & Repair", "Bahrain", "MEast", "mid", 26.16, 50.66, [
        ("VLCC Dock", "graving", 375, 70, 13.0, 500000, [80]),
        ("Floating Dock DD3", "floating", 240, 42, 8.5, 90000, [40]),
    ]),
    ("N-KOM (Nakilat-Keppel Qatar)", "Qatar", "MEast", "mid", 25.90, 51.55, [
        ("Graving Dock 1", "graving", 400, 80, 14.0, 500000, [100]),
        ("Graving Dock 2", "graving", 360, 66, 12.5, 300000, [60]),
    ]),
    ("Oman Drydock Company (Duqm)", "Oman", "MEast", "mid", 19.66, 57.70, [
        ("Dock 1", "graving", 410, 80, 14.0, 600000, [120]),
        ("Dock 2", "graving", 410, 95, 14.0, 600000, [120]),
    ]),
    ("Albwardy Damen (Sharjah)", "UAE", "MEast", "mid", 25.35, 55.39, [
        ("Floating Dock", "floating", 235, 40, 8.0, 85000, [35]),
    ]),
    # ---------------- India subcontinent
    ("Colombo Dockyard", "Sri Lanka", "ISC", "low", 6.95, 79.84, [
        ("Dock 3", "graving", 336, 43, 9.5, 125000, [50]),
        ("Dock 4", "graving", 223, 30, 8.0, 45000, [30]),
    ]),
    ("Cochin Shipyard", "India", "ISC", "low", 9.97, 76.27, [
        ("Ship Repair Dock", "graving", 270, 45, 9.0, 125000, [50]),
        ("ISRF Dock", "graving", 130, 25, 6.0, 20000, [20]),
    ]),
    ("Hindustan Shipyard (Visakhapatnam)", "India", "ISC", "low", 17.69, 83.28, [
        ("Dry Dock", "graving", 244, 38, 8.5, 70000, [40]),
    ]),
    ("L&T Kattupalli", "India", "ISC", "low", 13.30, 80.35, [
        ("Dry Dock", "graving", 300, 60, 10.0, 180000, [60]),
    ]),
    ("Chattogram Dry Dock", "Bangladesh", "ISC", "low", 22.24, 91.72, [
        ("Dry Dock", "graving", 210, 32, 8.0, 45000, [30]),
    ]),
    ("Pakistan Karachi Shipyard", "Pakistan", "ISC", "low", 24.82, 66.97, [
        ("Dry Dock", "graving", 216, 33, 8.5, 55000, [30]),
    ]),
    # ---------------- Far East (China / Korea)
    ("COSCO Shipping Zhoushan", "China", "FarEast", "mid", 30.03, 122.10, [
        ("No.1 Dock", "graving", 365, 80, 13.5, 350000, [80, 60]),
        ("No.2 Dock", "graving", 300, 58, 11.5, 200000, [50]),
    ]),
    ("COSCO Shipping Dalian", "China", "FarEast", "mid", 38.93, 121.63, [
        ("No.1 Dock", "graving", 365, 80, 13.5, 350000, [80]),
    ]),
    ("COSCO Shipping Guangdong", "China", "FarEast", "mid", 22.76, 113.10, [
        ("Dock A", "graving", 350, 66, 12.5, 300000, [60]),
    ]),
    ("Huarun Dadong Dockyard (Shanghai)", "China", "FarEast", "mid", 31.36, 121.68, [
        ("No.1 Dock", "graving", 365, 76, 13.0, 300000, [80]),
        ("No.2 Dock", "graving", 265, 50, 10.0, 120000, [50]),
    ]),
    ("China United Dockyard (Weihai)", "China", "FarEast", "mid", 37.51, 122.12, [
        ("Dock 1", "graving", 300, 58, 11.0, 200000, [50]),
    ]),
    ("Zhoushan IMC-YY", "China", "FarEast", "low", 29.95, 122.30, [
        ("Floating Dock", "floating", 255, 45, 8.5, 100000, [40]),
    ]),
    ("K Shipbuilding (Jinhae)", "South Korea", "FarEast", "high", 35.13, 128.66, [
        ("Dock 2", "graving", 320, 60, 11.5, 250000, [60]),
    ]),
    # ---------------- Mediterranean / Black Sea
    ("Besiktas Shipyard (Yalova)", "Turkey", "Med", "mid", 40.68, 29.28, [
        ("Floating Dock 1", "floating", 290, 46, 8.5, 150000, [40]),
        ("Floating Dock 2", "floating", 245, 40, 8.0, 90000, [35]),
    ]),
    ("Gemak Group (Tuzla)", "Turkey", "Med", "mid", 40.83, 29.30, [
        ("Floating Dock", "floating", 280, 45, 8.5, 140000, [40]),
    ]),
    ("Desan Shipyard (Tuzla)", "Turkey", "Med", "mid", 40.84, 29.31, [
        ("Dry Dock", "graving", 300, 50, 9.5, 180000, [50]),
    ]),
    ("Sedef Shipyard (Tuzla)", "Turkey", "Med", "mid", 40.83, 29.29, [
        ("Floating Dock", "floating", 255, 42, 8.0, 100000, [35]),
    ]),
    ("Palumbo Malta Superyachts & Repair", "Malta", "Med", "mid", 35.89, 14.51, [
        ("No.6 Dock", "graving", 360, 62, 12.0, 300000, [60]),
        ("No.4 Dock", "graving", 220, 32, 8.0, 50000, [30]),
    ]),
    ("Gibdock (Gibraltar)", "Gibraltar", "Med", "high", 36.14, -5.36, [
        ("No.1 Dock", "graving", 300, 46, 9.0, 100000, [50]),
        ("No.2 Dock", "graving", 200, 28, 7.5, 35000, [30]),
    ]),
    ("Hellenic Shipyards (Skaramangas)", "Greece", "Med", "mid", 38.00, 23.60, [
        ("No.3 Dock", "graving", 290, 45, 9.0, 100000, [50]),
    ]),
    ("Adriatic Croatia Viktor Lenac", "Croatia", "Med", "mid", 45.32, 14.45, [
        ("Floating Dock", "floating", 245, 40, 8.0, 90000, [35]),
    ]),
    # ---------------- Northern Europe
    ("Remontowa Ship Repair (Gdansk)", "Poland", "NEur", "high", 54.39, 18.68, [
        ("Dock 5", "floating", 380, 70, 12.0, 300000, [60]),
        ("Dock 4", "floating", 250, 42, 8.5, 100000, [40]),
    ]),
    ("Fayard (Odense)", "Denmark", "NEur", "high", 55.48, 10.55, [
        ("Dock 1", "graving", 415, 90, 14.0, 500000, [80]),
        ("Dock 2", "graving", 260, 45, 9.0, 120000, [50]),
    ]),
    ("Damen Verolme (Rotterdam)", "Netherlands", "NEur", "high", 51.89, 4.25, [
        ("Dock 6", "graving", 405, 90, 12.0, 500000, [80]),
    ]),
    ("Damen Shiprepair Brest", "France", "NEur", "high", 48.38, -4.50, [
        ("Dock 3", "graving", 420, 80, 13.0, 500000, [80]),
    ]),
    ("Blohm+Voss (Hamburg)", "Germany", "NEur", "high", 53.54, 9.96, [
        ("Dock Elbe 17", "graving", 351, 59, 11.5, 250000, [60]),
    ]),
    ("Lloyd Werft (Bremerhaven)", "Germany", "NEur", "high", 53.55, 8.58, [
        ("Kaiserdock II", "graving", 335, 46, 9.5, 120000, [50]),
    ]),
    ("Astander (Santander)", "Spain", "NEur", "mid", 43.46, -3.79, [
        ("Dock 3", "graving", 235, 40, 8.5, 90000, [40]),
    ]),
    ("Navantia (Cadiz)", "Spain", "NEur", "mid", 36.53, -6.20, [
        ("No.4 Dock", "graving", 400, 76, 13.0, 400000, [80]),
    ]),
    # ---------------- Americas
    ("Grand Bahama Shipyard (Freeport)", "Bahamas", "Am", "mid", 26.53, -78.77, [
        ("Dock 1", "floating", 275, 47, 8.5, 130000, [40]),
        ("Dock 2", "floating", 227, 40, 8.0, 90000, [35]),
    ]),
    ("Detyens Shipyards (Charleston)", "USA", "Am", "high", 32.86, -79.96, [
        ("Dry Dock 4", "graving", 231, 38, 8.5, 70000, [40]),
    ]),
    ("Vigor (Portland)", "USA", "Am", "high", 45.60, -122.72, [
        ("Floating Dry Dock", "floating", 290, 50, 9.0, 120000, [40]),
    ]),
    ("Seaspan Vancouver Drydock", "Canada", "Am", "high", 49.31, -123.08, [
        ("Floating Dock", "floating", 235, 40, 8.0, 90000, [35]),
    ]),
    ("EBRASA / Estaleiro Jurong (Aracruz)", "Brazil", "Am", "mid", -19.83, -40.07, [
        ("Dry Dock", "graving", 350, 60, 11.0, 250000, [60]),
    ]),
    ("Dormac (Durban)", "South Africa", "Am", "mid", -29.87, 31.03, [
        ("Floating Dock", "floating", 235, 40, 8.0, 85000, [35]),
    ]),
]


def build() -> list[dict]:
    out = []
    for name, country, region, band, lat, lon, docks in YARDS:
        out.append({
            "name": name,
            "country": country,
            "region": region,
            "labor_rate_band": band,
            "lat": lat,
            "lon": lon,
            "notes": "Planning-grade dock data — approximate, for shortlisting only.",
            "docks": [
                {
                    "name": d[0], "kind": d[1], "length_m": d[2], "beam_m": d[3],
                    "depth_over_blocks_m": d[4], "max_dwt": d[5], "cranes_json": d[6],
                }
                for d in docks
            ],
        })
    return out


if __name__ == "__main__":
    data = build()
    out = Path(__file__).with_name("yards.json")
    out.write_text(json.dumps(data, indent=2))
    ndocks = sum(len(y["docks"]) for y in data)
    print(f"wrote {len(data)} yards, {ndocks} docks -> {out}")

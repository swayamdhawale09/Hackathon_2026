"""
ResourceShift AI - Synthetic Water Telemetry Generator
------------------------------------------------------
Generates exactly 28 days of hourly readings (672 rows) for building water consumption.

Units:
- Volume: Litres (L)
- Rate: Litres per hour (L/hr)

Realistic Patterns:
- Daytime academic activity (toilets, sinks, lab water): 250 - 750 L/hr
- Normal overnight baseload (minimal leaks, safety systems): 10 - 25 L/hr
- 4 documented after-hours plumbing / cooling anomalies (28 anomalous hours).
"""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

DEFAULT_BUILDING_ID = "ENG_HALL_01"
DEFAULT_START_TIME = "2026-10-01T00:00:00"
TOTAL_DAYS = 28
HOURS_PER_DAY = 24
TOTAL_HOURS = TOTAL_DAYS * HOURS_PER_DAY  # Exactly 672 rows
RANDOM_SEED = 42

WATER_ANOMALIES = [
    {
        "id": "WATER_ANOM_1_FLUSHOMETER",
        "description": "Floor 2 restroom flushometer valve diaphragm stuck open.",
        "start_day": 4,
        "start_hour": 22,
        "duration_hours": 7,
        "equipment_type": "PLUMBING_FIXTURE",
        "equipment_notes": "Second-floor restroom flushometer diaphragm valve stuck open continuously.",
        "excess_mean_litres": 350.0,
        "excess_noise_std": 12.0,
    },
    {
        "id": "WATER_ANOM_2_IRRIGATION",
        "description": "North quad irrigation zone 4 solenoid stuck open overnight.",
        "start_day": 10,
        "start_hour": 21,
        "duration_hours": 7,
        "equipment_type": "IRRIGATION",
        "equipment_notes": "North quad landscape irrigation solenoid valve stuck open after automatic cycle.",
        "excess_mean_litres": 550.0,
        "excess_noise_std": 18.0,
    },
    {
        "id": "WATER_ANOM_3_LAB_RO",
        "description": "Chemistry research lab deionized / RO water continuous polishing bypass open.",
        "start_day": 16,
        "start_hour": 23,
        "duration_hours": 7,
        "equipment_type": "LAB_WATER",
        "equipment_notes": "Chemistry research lab deionized / RO water continuous polishing bypass valve left open.",
        "excess_mean_litres": 280.0,
        "excess_noise_std": 10.0,
    },
    {
        "id": "WATER_ANOM_4_COOLING_TOWER",
        "description": "Cooling tower makeup float valve jammed below cutoff.",
        "start_day": 23,
        "start_hour": 22,
        "duration_hours": 7,
        "equipment_type": "COOLING_TOWER",
        "equipment_notes": "Central plant cooling tower evaporative makeup float valve jammed below cutoff.",
        "excess_mean_litres": 480.0,
        "excess_noise_std": 15.0,
    },
]


def generate_water_data(
    building_id: str = DEFAULT_BUILDING_ID,
    start_time: str = DEFAULT_START_TIME,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generates exactly 672 hourly rows of synthetic building water consumption."""
    rng = np.random.default_rng(seed)
    start_dt = datetime.datetime.fromisoformat(start_time)

    anomaly_map: Dict[int, Dict[str, Any]] = {}
    for anom in WATER_ANOMALIES:
        start_hour = anom["start_day"] * 24 + anom["start_hour"]
        for h in range(anom["duration_hours"]):
            anomaly_map[start_hour + h] = anom

    rows: List[Dict[str, Any]] = []
    for hour_idx in range(TOTAL_HOURS):
        current_dt = start_dt + datetime.timedelta(hours=hour_idx)
        hour_of_day = current_dt.hour
        is_weekend = current_dt.weekday() >= 5
        scheduled_open = (not is_weekend) and (7 <= hour_of_day < 20)

        # Base idle leakage/float topup
        base_idle = 16.0 + rng.normal(0, 1.2)

        if scheduled_open:
            # Daytime usage driven by occupancy
            day_progress = (hour_of_day - 7) / 13.0
            bell = np.sin(day_progress * np.pi) ** 1.2
            usage = 420.0 * bell + rng.normal(0, 25.0)
            litres = max(40.0, base_idle + usage)
            occupancy = int(max(15, 210 * bell + rng.integers(-15, 16)))
            equipment_type = "DOMESTIC_PLUMBING"
            equipment_notes = "Normal operational daytime water demand."
        elif is_weekend and (9 <= hour_of_day < 17):
            litres = base_idle + 75.0 + rng.normal(0, 8.0)
            occupancy = int(max(1, rng.integers(2, 10)))
            equipment_type = "DOMESTIC_PLUMBING"
            equipment_notes = "Weekend quiet hours; light facility usage."
        else:
            litres = max(8.0, base_idle + rng.normal(0, 1.5))
            occupancy = int(rng.choice([0, 0, 0, 1], p=[0.75, 0.15, 0.08, 0.02]))
            equipment_type = "BASELOAD"
            equipment_notes = "Normal overnight baseload; no active fixtures."

        if hour_idx in anomaly_map:
            anom = anomaly_map[hour_idx]
            injected = anom["excess_mean_litres"] + rng.normal(0, anom["excess_noise_std"])
            litres += max(50.0, injected)
            equipment_type = anom["equipment_type"]
            equipment_notes = anom["equipment_notes"]
            is_injected_anomaly = True
        else:
            is_injected_anomaly = False

        rows.append({
            "timestamp": current_dt.isoformat(),
            "building_id": building_id,
            "resource_type": "water",
            "consumption": round(float(litres), 2),
            "unit": "L",
            "occupancy": int(occupancy),
            "scheduled_open": bool(scheduled_open),
            "equipment_type": str(equipment_type),
            "equipment_notes": str(equipment_notes),
            "is_injected_anomaly": bool(is_injected_anomaly),
        })

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic hourly water consumption data.")
    parser.add_argument("--output", "-o", type=str, default="data/sample_water_readings.csv")
    parser.add_argument("--seed", "-s", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    df = generate_water_data(seed=args.seed)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Generated {len(df)} water readings to '{args.output}'. Injected anomalies: {df['is_injected_anomaly'].sum()} hours.")


if __name__ == "__main__":
    main()

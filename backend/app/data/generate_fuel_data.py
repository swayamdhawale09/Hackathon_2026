"""
ResourceShift AI - Synthetic Fuel Telemetry Generator
----------------------------------------------------
Generates exactly 28 days of hourly readings (672 rows) for building fuel oil / diesel consumption.

Units:
- Volume: Litres (L)
- Rate: Litres per hour (L/hr)

Realistic Patterns:
- Heating boilers morning warmup (05:00 - 08:00 weekdays): 15 - 28 L/hr
- Weekly emergency generator test (Tuesdays 10:00 - 11:00): ~18 L/hr
- Normal overnight standby: 0.0 - 1.5 L/hr
- 4 documented after-hours fuel waste incidents (28 anomalous hours).
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

FUEL_ANOMALIES = [
    {
        "id": "FUEL_ANOM_1_BOILER_STUCK",
        "description": "Hydronic boiler burner 2 stuck at high-fire overnight due to aquastat fault.",
        "start_day": 5,
        "start_hour": 22,
        "duration_hours": 7,
        "equipment_type": "HEATING_BOILER",
        "equipment_notes": "Hydronic boiler burner 2 stuck at high-fire overnight due to faulty aquastat sensor.",
        "excess_mean_litres": 38.0,
        "excess_noise_std": 1.5,
    },
    {
        "id": "FUEL_ANOM_2_PUMP_BYPASS",
        "description": "Day-tank fuel recirculation transfer pump relief valve bypassing continuously.",
        "start_day": 11,
        "start_hour": 23,
        "duration_hours": 7,
        "equipment_type": "FUEL_SYSTEM",
        "equipment_notes": "Day-tank fuel recirculation transfer pump relief valve bypassing continuously to bulk storage.",
        "excess_mean_litres": 26.0,
        "excess_noise_std": 1.2,
    },
    {
        "id": "FUEL_ANOM_3_WEEKEND_OVERRIDE",
        "description": "Weekend night boiler setback failed; burners cycling at 80% duty on empty facility.",
        "start_day": 18,
        "start_hour": 21,
        "duration_hours": 7,
        "equipment_type": "HEATING_BOILER",
        "equipment_notes": "Weekend night boiler setback failed; dual burners cycling at 80% duty on empty facility.",
        "excess_mean_litres": 42.0,
        "excess_noise_std": 1.8,
    },
    {
        "id": "FUEL_ANOM_4_GENERATOR_LEAK",
        "description": "Auxiliary generator fuel line pressure relief valve weeping into containment sump.",
        "start_day": 24,
        "start_hour": 22,
        "duration_hours": 7,
        "equipment_type": "EMERGENCY_GENERATOR",
        "equipment_notes": "Auxiliary generator fuel line pressure relief valve weeping into containment sump.",
        "excess_mean_litres": 24.0,
        "excess_noise_std": 1.0,
    },
]


def generate_fuel_data(
    building_id: str = DEFAULT_BUILDING_ID,
    start_time: str = DEFAULT_START_TIME,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generates exactly 672 hourly rows of synthetic building fuel consumption."""
    rng = np.random.default_rng(seed)
    start_dt = datetime.datetime.fromisoformat(start_time)

    anomaly_map: Dict[int, Dict[str, Any]] = {}
    for anom in FUEL_ANOMALIES:
        start_hour = anom["start_day"] * 24 + anom["start_hour"]
        for h in range(anom["duration_hours"]):
            anomaly_map[start_hour + h] = anom

    rows: List[Dict[str, Any]] = []
    for hour_idx in range(TOTAL_HOURS):
        current_dt = start_dt + datetime.timedelta(hours=hour_idx)
        hour_of_day = current_dt.hour
        is_weekend = current_dt.weekday() >= 5
        weekday = current_dt.weekday()
        scheduled_open = (not is_weekend) and (7 <= hour_of_day < 20)

        # Baseline fuel behavior:
        # Weekday morning pre-heat (05:00 - 08:00)
        if (not is_weekend) and (5 <= hour_of_day < 8):
            litres = 18.0 + rng.normal(0, 2.0)
            equipment_type = "HEATING_BOILER"
            equipment_notes = "Scheduled morning building hydronic warmup cycle."
            occupancy = 2
        # Tuesday generator test (10:00 - 11:00)
        elif weekday == 1 and hour_of_day == 10:
            litres = 18.5 + rng.normal(0, 1.0)
            equipment_type = "EMERGENCY_GENERATOR"
            equipment_notes = "Mandatory weekly emergency diesel generator test run."
            occupancy = 120
        elif scheduled_open:
            litres = max(0.0, rng.normal(1.0, 0.5))
            equipment_type = "STANDBY"
            equipment_notes = "Daytime standby boiler pilot; ambient heating maintained."
            occupancy = int(max(15, 180 * np.sin((hour_of_day - 7) / 13.0 * np.pi) + rng.integers(-10, 11)))
        else:
            # Overnight idle
            litres = max(0.0, rng.normal(0.2, 0.1))
            equipment_type = "STANDBY"
            equipment_notes = "Overnight standby; burners deactivated."
            occupancy = int(rng.choice([0, 0, 1], p=[0.85, 0.12, 0.03]))

        if hour_idx in anomaly_map:
            anom = anomaly_map[hour_idx]
            injected = anom["excess_mean_litres"] + rng.normal(0, anom["excess_noise_std"])
            litres += max(5.0, injected)
            equipment_type = anom["equipment_type"]
            equipment_notes = anom["equipment_notes"]
            is_injected_anomaly = True
        else:
            is_injected_anomaly = False

        rows.append({
            "timestamp": current_dt.isoformat(),
            "building_id": building_id,
            "resource_type": "fuel",
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
    parser = argparse.ArgumentParser(description="Generate synthetic hourly fuel consumption data.")
    parser.add_argument("--output", "-o", type=str, default="data/sample_fuel_readings.csv")
    parser.add_argument("--seed", "-s", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    df = generate_fuel_data(seed=args.seed)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Generated {len(df)} fuel readings to '{args.output}'. Injected anomalies: {df['is_injected_anomaly'].sum()} hours.")


if __name__ == "__main__":
    main()

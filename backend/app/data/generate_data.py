"""
ResourceShift AI - Synthetic Electricity Telemetry Generator
------------------------------------------------------------
Generates exactly 28 days of hourly readings (672 rows) for a single simulated
college building ("ENG_HALL_01").

Dataset Scope & Realism:
- Captures diurnal patterns (daytime academic activity vs. low night baseload).
- Accounts for weekday vs. weekend scheduling.
- Injects 6 documented after-hours energy waste anomalies.
- Uses a deterministic seed (default: 42) for 100% reproducibility.

Real-World Schema Mapping:
In a production deployment, this schema maps directly to sub-metered BMS
(Building Management System) telemetry via BACnet/Modbus/MQTT feeds or utility
interval data (Green Button / AMI 15-min or 60-min interval data).
"""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import pandas as pd

DEFAULT_BUILDING_ID = "ENG_HALL_01"
DEFAULT_START_TIME = "2026-10-01T00:00:00"
TOTAL_DAYS = 28
HOURS_PER_DAY = 24
TOTAL_HOURS = TOTAL_DAYS * HOURS_PER_DAY  # Exactly 672 rows
RANDOM_SEED = 42

# 6 Documented Anomaly Scenarios (After-Hours Waste Events)
DOCUMENTED_ANOMALIES = [
    {
        "id": "ANOMALY_1_HVAC_OVERRIDE",
        "description": "Floor 3 AHU-3 chiller override left running at daytime cooling (66F) overnight.",
        "start_day": 3,   # Day 3
        "start_hour": 21, # 21:00
        "duration_hours": 7, # Through 03:00 next day
        "equipment_type": "HVAC",
        "equipment_notes": "Chiller unit AHU-3 override set to continuous cooling at 66F overnight after scheduled maintenance.",
        "excess_mean_kwh": 115.0,
        "excess_noise_std": 4.0,
    },
    {
        "id": "ANOMALY_2_LAB_FURNACE",
        "description": "Robotics & Materials Lab vacuum furnace left in standby bake cycle.",
        "start_day": 8,
        "start_hour": 22,
        "duration_hours": 8,
        "equipment_type": "LAB_EQUIPMENT",
        "equipment_notes": "Robotics & Materials Lab vacuum furnace left energized in unmonitored standby bake cycle.",
        "excess_mean_kwh": 95.0,
        "excess_noise_std": 3.5,
    },
    {
        "id": "ANOMALY_3_AUDITORIUM_LIGHTS",
        "description": "Auditorium 201 theatrical lights and 2nd floor corridors banked at 100%.",
        "start_day": 13,
        "start_hour": 20,
        "duration_hours": 11,
        "equipment_type": "LIGHTING",
        "equipment_notes": "Auditorium 201 theatrical spotlights and second-floor corridor lighting banked at 100% capacity.",
        "excess_mean_kwh": 68.0,
        "excess_noise_std": 2.5,
    },
    {
        "id": "ANOMALY_4_PUMP_RELAY_STUCK",
        "description": "Cooling tower auxiliary pump relay stuck mechanically closed.",
        "start_day": 17,
        "start_hour": 23,
        "duration_hours": 8,
        "equipment_type": "HVAC",
        "equipment_notes": "Cooling tower auxiliary circulation pump relay contactor mechanically stuck in closed position.",
        "excess_mean_kwh": 85.0,
        "excess_noise_std": 3.0,
    },
    {
        "id": "ANOMALY_5_UNMANAGED_COMPUTE",
        "description": "High-performance GPU compute cluster batch simulations running without eco-mode.",
        "start_day": 21,
        "start_hour": 21,
        "duration_hours": 8,
        "equipment_type": "LAB_EQUIPMENT",
        "equipment_notes": "High-performance computing cluster running unmanaged distributed simulations overnight without eco-governor.",
        "excess_mean_kwh": 110.0,
        "excess_noise_std": 4.0,
    },
    {
        "id": "ANOMALY_6_COMPRESSOR_LEAK",
        "description": "Pneumatic control compressor cycling at 95% due to 4th floor damper seal tear.",
        "start_day": 25,
        "start_hour": 22,
        "duration_hours": 8,
        "equipment_type": "HVAC",
        "equipment_notes": "Pneumatic control air compressor duty cycle at 95% due to ruptured damper seal on Floor 4.",
        "excess_mean_kwh": 76.0,
        "excess_noise_std": 2.8,
    },
]


def generate_electricity_data(
    building_id: str = DEFAULT_BUILDING_ID,
    start_time: str = DEFAULT_START_TIME,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Generates exactly 672 hourly rows of synthetic building electricity consumption.

    Args:
        building_id: Unique identifier for the building.
        start_time: ISO-8601 string for start timestamp.
        seed: Random seed for deterministic reproducibility.

    Returns:
        pd.DataFrame with 672 rows and 8 defined columns.
    """
    rng = np.random.default_rng(seed)
    start_dt = datetime.datetime.fromisoformat(start_time)

    rows: List[Dict[str, Any]] = []

    # Pre-index anomaly time windows for fast, exact lookup
    anomaly_map: Dict[int, Dict[str, Any]] = {}
    for anomaly in DOCUMENTED_ANOMALIES:
        start_global_hour = anomaly["start_day"] * 24 + anomaly["start_hour"]
        for h in range(anomaly["duration_hours"]):
            global_hour_idx = start_global_hour + h
            anomaly_map[global_hour_idx] = anomaly

    for hour_idx in range(TOTAL_HOURS):
        current_dt = start_dt + datetime.timedelta(hours=hour_idx)
        hour_of_day = current_dt.hour
        weekday = current_dt.weekday()  # 0=Monday, 6=Sunday
        is_weekend = weekday >= 5

        # Academic building operating schedule:
        # Weekdays: Open 07:00 to 20:00 (hours 7 to 19 inclusive)
        # Weekends: Closed (scheduled_open = False)
        if not is_weekend and (7 <= hour_of_day < 20):
            scheduled_open = True
        else:
            scheduled_open = False

        # --- Baseline Load Calculation ---
        # 1. Base idle load (continuous server room, exit lights, standby controls)
        base_idle = 42.0 + rng.normal(0, 1.5)

        # 2. Activity addition
        if scheduled_open:
            # Daytime bell-curve peaking around 13:00-14:00
            day_progress = (hour_of_day - 7) / 13.0  # 0 to 1
            activity_multiplier = np.sin(day_progress * np.pi) ** 1.3
            daytime_load = 180.0 * activity_multiplier + rng.normal(0, 8.0)
            electricity_kwh = max(60.0, base_idle + daytime_load)

            # Daytime occupancy
            occupancy = int(max(15, 210 * activity_multiplier + rng.integers(-15, 16)))
            equipment_type = "MIXED"
            equipment_notes = "Normal operational daytime profile; HVAC and academic lighting active."
        elif is_weekend and (9 <= hour_of_day < 17):
            # Weekend light study hours (unscheduled open)
            weekend_load = 22.0 + rng.normal(0, 3.0)
            electricity_kwh = base_idle + weekend_load
            occupancy = int(max(1, rng.integers(2, 10)))
            equipment_type = "BASELOAD"
            equipment_notes = "Weekend quiet hours; library/study access."
        else:
            # Normal overnight after-hours
            # Setback HVAC + safety baseload
            electricity_kwh = max(35.0, base_idle + rng.normal(0, 2.0))
            # 0 occupancy, occasional night security walk (1-2)
            occupancy = int(rng.choice([0, 0, 0, 1], p=[0.75, 0.15, 0.08, 0.02]))
            equipment_type = "BASELOAD"
            equipment_notes = "Normal after-hours idle state; baseline servers and safety systems."

        # --- Check for Anomaly Injection ---
        if hour_idx in anomaly_map:
            anomaly = anomaly_map[hour_idx]
            injected_excess = anomaly["excess_mean_kwh"] + rng.normal(0, anomaly["excess_noise_std"])
            electricity_kwh += max(10.0, injected_excess)
            equipment_type = anomaly["equipment_type"]
            equipment_notes = anomaly["equipment_notes"]
            is_injected_anomaly = True
        else:
            is_injected_anomaly = False

        rows.append({
            "timestamp": current_dt.isoformat(),
            "building_id": building_id,
            "electricity_kwh": round(float(electricity_kwh), 2),
            "occupancy": int(occupancy),
            "scheduled_open": bool(scheduled_open),
            "equipment_type": str(equipment_type),
            "equipment_notes": str(equipment_notes),
            "is_injected_anomaly": bool(is_injected_anomaly),
        })

    df = pd.DataFrame(rows)
    return df


def save_to_csv(df: pd.DataFrame, file_path: str | Path) -> None:
    """Saves DataFrame to CSV with directory creation and validation."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 28-day synthetic hourly electricity dataset for ResourceShift AI."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/sample_readings.csv",
        help="Destination path for the CSV output.",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=RANDOM_SEED,
        help="Random seed for reproducible telemetry.",
    )
    args = parser.parse_args()

    print(f"Generating synthetic electricity readings (seed={args.seed})...")
    df = generate_electricity_data(seed=args.seed)
    save_to_csv(df, args.output)
    print(f"Successfully generated {len(df)} rows to '{args.output}'.")
    print(f"Injected anomalies count: {df['is_injected_anomaly'].sum()} hours.")


if __name__ == "__main__":
    main()

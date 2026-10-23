"""
ResourceShift AI - In-Memory & File-Backed Multi-Resource Telemetry Store
--------------------------------------------------------------------------
Loads, caches, and indexes multi-resource telemetry (Electricity, Water, Fuel)
and pre-computes deterministic baseline anomalies.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from backend.app.core.analysis import (
    validate_readings,
    build_baseline,
    detect_anomalies,
    RESOURCE_CONFIGS,
)
from backend.app.data.generate_data import generate_electricity_data
from backend.app.data.generate_water_data import generate_water_data
from backend.app.data.generate_fuel_data import generate_fuel_data

ELECTRICITY_CSV = Path("data/sample_readings.csv")
WATER_CSV = Path("data/sample_water_readings.csv")
FUEL_CSV = Path("data/sample_fuel_readings.csv")


class TelemetryStore:
    """Manages telemetry datasets and detected anomalies across all resource types."""

    def __init__(self) -> None:
        self._telemetry: Dict[str, pd.DataFrame] = {}
        self._baselines: Dict[str, Dict[str, Any]] = {}
        self._anomalies: Dict[str, List[Dict[str, Any]]] = {}
        self._anomalies_by_id: Dict[str, Dict[str, Any]] = {}
        self._is_loaded = False

    def ensure_loaded(self) -> None:
        """Loads and processes all resource datasets on first access."""
        if self._is_loaded:
            return

        # 1. Electricity
        if not ELECTRICITY_CSV.exists():
            df_elec = generate_electricity_data()
            ELECTRICITY_CSV.parent.mkdir(parents=True, exist_ok=True)
            df_elec.to_csv(ELECTRICITY_CSV, index=False)
        else:
            df_elec = pd.read_csv(ELECTRICITY_CSV)

        v_elec = validate_readings(df_elec, resource_type="electricity")
        v_elec["resource_type"] = "electricity"
        v_elec["unit"] = "kWh"
        b_elec = build_baseline(v_elec, resource_type="electricity")
        a_elec = detect_anomalies(v_elec, b_elec, resource_type="electricity")

        self._telemetry["electricity"] = v_elec
        self._baselines["electricity"] = b_elec
        self._anomalies["electricity"] = a_elec

        # 2. Water
        if not WATER_CSV.exists():
            df_water = generate_water_data()
            WATER_CSV.parent.mkdir(parents=True, exist_ok=True)
            df_water.to_csv(WATER_CSV, index=False)
        else:
            df_water = pd.read_csv(WATER_CSV)

        v_water = validate_readings(df_water, resource_type="water")
        v_water["resource_type"] = "water"
        v_water["unit"] = "L"
        b_water = build_baseline(v_water, resource_type="water")
        a_water = detect_anomalies(v_water, b_water, resource_type="water")

        self._telemetry["water"] = v_water
        self._baselines["water"] = b_water
        self._anomalies["water"] = a_water

        # 3. Fuel
        if not FUEL_CSV.exists():
            df_fuel = generate_fuel_data()
            FUEL_CSV.parent.mkdir(parents=True, exist_ok=True)
            df_fuel.to_csv(FUEL_CSV, index=False)
        else:
            df_fuel = pd.read_csv(FUEL_CSV)

        v_fuel = validate_readings(df_fuel, resource_type="fuel")
        v_fuel["resource_type"] = "fuel"
        v_fuel["unit"] = "L"
        b_fuel = build_baseline(v_fuel, resource_type="fuel")
        a_fuel = detect_anomalies(v_fuel, b_fuel, resource_type="fuel")

        self._telemetry["fuel"] = v_fuel
        self._baselines["fuel"] = b_fuel
        self._anomalies["fuel"] = a_fuel

        # Index anomalies by ID
        self._anomalies_by_id = {}
        for r_type, anom_list in self._anomalies.items():
            for anom in anom_list:
                self._anomalies_by_id[anom["anomaly_id"]] = anom

        self._is_loaded = True

    def get_telemetry(
        self,
        resource_type: Optional[str] = None,
        building_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Queries telemetry with optional filters and pagination."""
        self.ensure_loaded()

        frames: List[pd.DataFrame] = []
        if resource_type:
            r_type = resource_type.lower()
            if r_type in self._telemetry:
                frames.append(self._telemetry[r_type])
        else:
            frames = list(self._telemetry.values())

        if not frames:
            return {"total": 0, "limit": limit, "offset": offset, "readings": []}

        combined = pd.concat(frames, ignore_index=True)

        if building_id:
            combined = combined[combined["building_id"] == building_id]

        if start_time:
            combined = combined[combined["timestamp"] >= start_time]

        if end_time:
            combined = combined[combined["timestamp"] <= end_time]

        # Sort chronologically
        combined = combined.sort_values(by=["timestamp", "resource_type"])
        total_count = len(combined)

        paged = combined.iloc[offset : offset + limit]

        # Convert to serializable records
        records = []
        for _, row in paged.iterrows():
            records.append({
                "timestamp": str(row["timestamp"]),
                "building_id": str(row["building_id"]),
                "resource_type": str(row["resource_type"]),
                "consumption": float(row["consumption"]),
                "unit": str(row.get("unit", RESOURCE_CONFIGS.get(str(row["resource_type"]), {}).get("unit", ""))),
                "occupancy": int(row["occupancy"]),
                "scheduled_open": bool(row["scheduled_open"]),
                "equipment_type": str(row.get("equipment_type", "")),
                "equipment_notes": str(row.get("equipment_notes", "")),
            })

        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "readings": records,
        }

    def get_anomalies(
        self,
        resource_type: Optional[str] = None,
        severity: Optional[str] = None,
        building_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Queries pre-computed deterministic anomalies."""
        self.ensure_loaded()

        all_anoms: List[Dict[str, Any]] = []
        if resource_type:
            r_type = resource_type.lower()
            all_anoms = list(self._anomalies.get(r_type, []))
        else:
            for anom_list in self._anomalies.values():
                all_anoms.extend(anom_list)

        if severity:
            all_anoms = [a for a in all_anoms if a.get("severity") == severity.lower()]

        if building_id:
            all_anoms = [a for a in all_anoms if a.get("building_id") == building_id]

        all_anoms.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        total_count = len(all_anoms)

        return {
            "total_anomalies": total_count,
            "limit": limit,
            "anomalies": all_anoms[:limit],
        }

    def get_anomaly_by_id(self, anomaly_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single anomaly by its unique identifier."""
        self.ensure_loaded()
        return self._anomalies_by_id.get(anomaly_id)


# Global singleton instance
store = TelemetryStore()

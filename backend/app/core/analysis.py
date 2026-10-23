"""
ResourceShift AI - Deterministic Multi-Resource Analysis & Anomaly Detection
-----------------------------------------------------------------------------
Core analytical module implementing deterministic validation, robust
statistical baseline modeling (median + MAD), threshold anomaly detection,
savings estimation, and performance evaluation for Electricity, Water, and Fuel.

Security & Architecture Invariants:
- Ground-truth labels ('is_injected_anomaly') are strictly excluded from
  baseline building and anomaly detection.
- All equipment notes and external strings are treated strictly as untrusted data.
- Calculations are strictly deterministic (Python). No LLM approximations.
- Proposes optimizations; never controls physical building infrastructure.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

# Multi-resource standard configuration parameters
RESOURCE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "electricity": {
        "unit": "kWh",
        "default_tariff": 0.14,       # $0.14 per kWh
        "default_co2": 0.42,          # 0.42 kg CO2 per kWh
        "default_min_excess": 28.0,   # Minimum excess kWh to trigger alert
        "min_std_floor": 2.5,         # Minimum scale floor
    },
    "water": {
        "unit": "L",
        "default_tariff": 0.005,      # $0.005 per Litre ($5.00 / 1,000 L)
        "default_co2": 0.0003,        # 0.0003 kg CO2 per Litre (embodied pumping/treatment)
        "default_min_excess": 100.0,  # Minimum excess Litres to trigger alert
        "min_std_floor": 2.0,
    },
    "fuel": {
        "unit": "L",
        "default_tariff": 1.15,       # $1.15 per Litre (heating oil / diesel)
        "default_co2": 2.68,          # 2.68 kg CO2 per Litre combusted
        "default_min_excess": 10.0,   # Minimum excess Litres to trigger alert
        "min_std_floor": 0.5,
    },
}

REQUIRED_BASE_COLUMNS = {
    "timestamp",
    "building_id",
    "occupancy",
    "scheduled_open",
}
REQUIRED_COLUMNS = REQUIRED_BASE_COLUMNS | {"electricity_kwh"}


def validate_readings(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    resource_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    Validates building resource readings schema and value constraints.
    Supports Electricity (kWh), Water (L), and Fuel (L).

    Validation rules:
    - Input must be a pandas DataFrame or non-empty list of dictionaries.
    - Required base columns must be present: timestamp, building_id, occupancy, scheduled_open.
    - Value column must be present: either 'electricity_kwh' or 'consumption'.
    - Timestamps must be valid ISO-8601 strings or datetime objects.
    - Consumption must be numeric and non-negative (>= 0).
    - Occupancy must be numeric and non-negative (>= 0).
    - Scheduled_open must be boolean or convertible to boolean.
    - Resource type (if present) must be one of: electricity, water, fuel.
    - Equipment notes are converted to string and treated strictly as untrusted text.

    Args:
        data: DataFrame or list of dictionaries containing telemetry readings.
        resource_type: Optional resource type constraint ('electricity', 'water', 'fuel').

    Returns:
        Validated pd.DataFrame with parsed datetime and typed columns.

    Raises:
        TypeError: If input data is not a DataFrame or list of dicts.
        ValueError: If input is empty, has missing columns, or contains invalid data.
    """
    if data is None:
        raise ValueError("Input data cannot be None.")

    if isinstance(data, list):
        if len(data) == 0:
            raise ValueError("Input data list is empty.")
        if not all(isinstance(item, dict) for item in data):
            raise TypeError("All items in data list must be dictionaries.")
        df = pd.DataFrame(data)
    elif isinstance(data, pd.DataFrame):
        if data.empty:
            raise ValueError("Input DataFrame is empty.")
        df = data.copy()
    else:
        raise TypeError(
            f"Input data must be a pandas DataFrame or list of dicts, got {type(data).__name__}."
        )

    # 1. Base required columns check
    missing_base = REQUIRED_BASE_COLUMNS - set(df.columns)
    if missing_base:
        raise ValueError(f"Missing required column(s): {sorted(list(missing_base))}")

    # Check for value column (either electricity_kwh or consumption)
    has_elec = "electricity_kwh" in df.columns
    has_consump = "consumption" in df.columns
    if not has_elec and not has_consump:
        raise ValueError("Missing required column(s): ['electricity_kwh' or 'consumption']")

    # Standardize value column: ensure both consumption and electricity_kwh exist
    if has_elec and not has_consump:
        df["consumption"] = df["electricity_kwh"]
    elif has_consump and not has_elec:
        df["electricity_kwh"] = df["consumption"]

    # 2. Resource type validation
    if "resource_type" in df.columns:
        invalid_types = set(df["resource_type"].dropna().unique()) - set(RESOURCE_CONFIGS.keys())
        if invalid_types:
            raise ValueError(f"Invalid resource_type found: {invalid_types}. Allowed: {list(RESOURCE_CONFIGS.keys())}")
    else:
        df["resource_type"] = resource_type if resource_type else "electricity"

    # 3. Timestamp validation and parsing
    try:
        df["_parsed_dt"] = pd.to_datetime(df["timestamp"], errors="raise")
    except Exception as exc:
        raise ValueError(f"Invalid timestamp format detected: {exc}") from exc

    if df["_parsed_dt"].isna().any():
        raise ValueError("One or more timestamps could not be parsed.")

    # 4. Consumption / Electricity kWh validation
    if not pd.api.types.is_numeric_dtype(df["consumption"]):
        try:
            df["consumption"] = pd.to_numeric(df["consumption"], errors="raise")
            df["electricity_kwh"] = df["consumption"]
        except Exception as exc:
            raise ValueError(f"consumption contains non-numeric values: {exc}") from exc

    if (df["consumption"] < 0).any():
        negative_vals = df[df["consumption"] < 0]["consumption"].tolist()
        raise ValueError(
            f"electricity_kwh must be non-negative. Found invalid values: {negative_vals[:3]}"
        )

    if df["consumption"].isna().any():
        raise ValueError("electricity_kwh contains NaN or null values.")

    # 5. Occupancy validation
    if not pd.api.types.is_numeric_dtype(df["occupancy"]):
        try:
            df["occupancy"] = pd.to_numeric(df["occupancy"], errors="raise")
        except Exception as exc:
            raise ValueError(f"occupancy contains non-numeric values: {exc}") from exc

    if (df["occupancy"] < 0).any():
        negative_occ = df[df["occupancy"] < 0]["occupancy"].tolist()
        raise ValueError(
            f"occupancy must be non-negative. Found invalid values: {negative_occ[:3]}"
        )

    if df["occupancy"].isna().any():
        raise ValueError("occupancy contains NaN or null values.")

    # 6. Scheduled_open validation
    if not pd.api.types.is_bool_dtype(df["scheduled_open"]):
        unique_vals = set(df["scheduled_open"].dropna().unique())
        allowed_bools = {True, False, 1, 0, "true", "false", "True", "False"}
        if not unique_vals.issubset(allowed_bools):
            raise ValueError(
                f"scheduled_open must be boolean, found invalid values: {unique_vals - allowed_bools}"
            )
        df["scheduled_open"] = df["scheduled_open"].astype(bool)

    # 7. Untrusted equipment notes handling: strictly cast to str
    if "equipment_notes" in df.columns:
        df["equipment_notes"] = df["equipment_notes"].fillna("").astype(str)

    # Helper time fields
    df["hour"] = df["_parsed_dt"].dt.hour
    df["is_weekend"] = df["_parsed_dt"].dt.weekday >= 5
    df = df.drop(columns=["_parsed_dt"])

    return df


def build_baseline(
    data: pd.DataFrame,
    min_std_floor: Optional[float] = None,
    resource_type: str = "electricity",
) -> Dict[str, Any]:
    """
    Builds a deterministic, explainable historical consumption baseline.

    Methodology:
    - Groups telemetry by (is_weekend, hour_of_day).
    - Uses median consumption as central expected baseline.
    - Uses Median Absolute Deviation (MAD scaled by 1.4826) as robust scale estimator.
    - Completely ignores ground-truth labels if present.
    - Supports electricity, water, and fuel with resource-calibrated variance floors.

    Args:
        data: Validated DataFrame of telemetry readings.
        min_std_floor: Optional minimum standard deviation floor. If None,
                       defaults to resource-calibrated floor.
        resource_type: Resource type ('electricity', 'water', 'fuel').

    Returns:
        Dictionary containing group baselines and global fallback statistics.
    """
    if "hour" not in data.columns or "is_weekend" not in data.columns:
        df = validate_readings(data, resource_type=resource_type)
    else:
        df = data.copy()

    val_col = "consumption" if "consumption" in df.columns else "electricity_kwh"
    res_type = str(df["resource_type"].iloc[0]) if "resource_type" in df.columns else resource_type
    res_cfg = RESOURCE_CONFIGS.get(res_type, RESOURCE_CONFIGS["electricity"])

    if min_std_floor is None:
        floor = float(res_cfg["min_std_floor"])
    else:
        floor = float(min_std_floor)

    feature_df = df[["hour", "is_weekend", val_col]].copy()

    # Global fallbacks
    global_median = float(feature_df[val_col].median())
    global_mean = float(feature_df[val_col].mean())
    global_mad = float(np.median(np.abs(feature_df[val_col] - global_median)))
    global_robust_std = max(floor, 1.4826 * global_mad)

    groups: Dict[Tuple[bool, int], Dict[str, float]] = {}

    grouped = feature_df.groupby(["is_weekend", "hour"])
    for (is_wknd, hr), group in grouped:
        count = len(group)
        if count == 0:
            continue

        median_val = float(group[val_col].median())
        mean_val = float(group[val_col].mean())

        mad_val = float(np.median(np.abs(group[val_col] - median_val)))
        robust_std = max(floor, 1.4826 * mad_val)

        raw_std = float(group[val_col].std(ddof=1)) if count > 1 else global_robust_std
        if np.isnan(raw_std) or raw_std < floor:
            raw_std = floor

        p10 = float(group[val_col].quantile(0.10))
        p90 = float(group[val_col].quantile(0.90))

        groups[(bool(is_wknd), int(hr))] = {
            "expected_kwh": round(median_val, 2),
            "expected_consumption": round(median_val, 2),
            "mean_kwh": round(mean_val, 2),
            "std_kwh": round(robust_std, 2),
            "raw_sample_std_kwh": round(raw_std, 2),
            "p10_kwh": round(p10, 2),
            "p90_kwh": round(p90, 2),
            "sample_count": count,
        }

    return {
        "groups": groups,
        "resource_type": res_type,
        "unit": res_cfg["unit"],
        "global_fallback": {
            "expected_kwh": round(global_median, 2),
            "expected_consumption": round(global_median, 2),
            "mean_kwh": round(global_mean, 2),
            "std_kwh": round(global_robust_std, 2),
        },
        "total_baseline_samples": len(feature_df),
    }


def detect_anomalies(
    data: pd.DataFrame,
    baseline: Dict[str, Any],
    z_threshold: float = 3.0,
    min_excess_kwh: Optional[float] = None,
    after_hours_only: bool = True,
    resource_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Deterministically detects suspicious resource waste by comparing actual
    consumption against expected baseline metrics.
    Supports Electricity, Water, and Fuel.

    Detection Invariants:
    - Never references or accesses 'is_injected_anomaly'.
    - Focuses on after-hours waste (when scheduled_open is False and/or low occupancy).
    - Requires statistical deviation (robust Z >= z_threshold) AND physical excess
      (excess >= min_excess) to prevent false alerts on baseline noise.

    Args:
        data: Telemetry readings DataFrame.
        baseline: Baseline dictionary generated by build_baseline().
        z_threshold: Standard deviations above baseline to flag (default: 3.0).
        min_excess_kwh: Minimum excess consumption in resource units to trigger alert.
                        If None, uses resource-calibrated default (28 kWh / 100 L / 10 L).
        after_hours_only: If True, restricts alerts to unscheduled / after-hours periods.
        resource_type: Resource type override ('electricity', 'water', 'fuel').

    Returns:
        List of structured anomaly dictionaries.
    """
    res_type = resource_type or baseline.get("resource_type", "electricity")
    res_cfg = RESOURCE_CONFIGS.get(res_type, RESOURCE_CONFIGS["electricity"])

    df = validate_readings(data, resource_type=res_type)
    groups = baseline.get("groups", {})
    fallback = baseline.get("global_fallback", {"expected_kwh": 50.0, "std_kwh": 5.0})

    if min_excess_kwh is None:
        min_excess = float(res_cfg["default_min_excess"])
    else:
        min_excess = float(min_excess_kwh)

    unit = res_cfg["unit"]
    anomalies: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        is_wknd = bool(row["is_weekend"])
        hr = int(row["hour"])
        actual_val = float(row["consumption"])
        scheduled_open = bool(row["scheduled_open"])
        occupancy = int(row["occupancy"])

        group_stats = groups.get((is_wknd, hr), fallback)
        expected_val = float(group_stats.get("expected_consumption", group_stats.get("expected_kwh", 0.0)))
        std_val = float(group_stats.get("std_kwh", 2.5))

        excess = actual_val - expected_val
        z_score = excess / std_val if std_val > 0 else 0.0

        is_after_hours = (not scheduled_open) or (occupancy <= 2 and (hr >= 20 or hr < 7))

        if after_hours_only and not is_after_hours:
            continue

        is_suspicious = (excess >= min_excess) and (z_score >= z_threshold)

        if is_suspicious:
            ratio = actual_val / expected_val if expected_val > 0 else 1.0

            # Severity scaling calibrated to resource
            if res_type == "water":
                if excess >= 500.0 or z_score >= 10.0:
                    severity = "critical"
                elif excess >= 350.0 or z_score >= 6.0:
                    severity = "high"
                elif excess >= 200.0 or z_score >= 4.0:
                    severity = "medium"
                else:
                    severity = "low"
            elif res_type == "fuel":
                if excess >= 35.0 or z_score >= 10.0:
                    severity = "critical"
                elif excess >= 25.0 or z_score >= 6.0:
                    severity = "high"
                elif excess >= 15.0 or z_score >= 4.0:
                    severity = "medium"
                else:
                    severity = "low"
            else:  # electricity
                if excess >= 100.0 or z_score >= 10.0:
                    severity = "critical"
                elif excess >= 70.0 or z_score >= 6.0:
                    severity = "high"
                elif excess >= 45.0 or z_score >= 4.0:
                    severity = "medium"
                else:
                    severity = "low"

            evidence = {
                "resource_type": res_type,
                "unit": unit,
                "z_score": round(float(z_score), 2),
                "ratio_to_baseline": round(float(ratio), 2),
                "scheduled_open": scheduled_open,
                "occupancy": occupancy,
                "hour_of_day": hr,
                "is_weekend": is_wknd,
                "equipment_type": str(row.get("equipment_type", "UNKNOWN")),
                "equipment_notes": str(row.get("equipment_notes", "")),
                "description": (
                    f"After-hours {res_type} usage of {actual_val:.1f} {unit} is {excess:.1f} {unit} "
                    f"({(ratio - 1.0) * 100:.0f}%) above expected baseline ({expected_val:.1f} {unit}) "
                    f"with occupancy={occupancy} at hour {hr:02d}:00."
                ),
            }

            anomaly_id = f"ANOM-{res_type.upper()[:4]}-{str(row['timestamp']).replace(':', '').replace('-', '')[:13]}"

            anomalies.append({
                "anomaly_id": anomaly_id,
                "reading_index": int(idx),
                "resource_type": res_type,
                "unit": unit,
                "timestamp": str(row["timestamp"]),
                "building_id": str(row["building_id"]),
                "actual_usage": round(actual_val, 2),
                "expected_usage": round(expected_val, 2),
                "excess_consumption": round(excess, 2),
                "severity": severity,
                "supporting_evidence": evidence,
            })

    return anomalies


def estimate_savings(
    actual_kwh: float,
    baseline_kwh: float,
    tariff_rate: Optional[float] = None,
    co2_factor: Optional[float] = None,
    resource_type: str = "electricity",
) -> Dict[str, Any]:
    """
    Calculates estimated excess energy/resource, cost savings, and carbon abatement.
    Supports Electricity (kWh), Water (L), and Fuel (L).

    Safety & Validation:
    - Tariff rate must be strictly positive (> 0).
    - CO2 factor must be non-negative (>= 0).
    - Actual and baseline values must be non-negative.
    - Prevents negative savings (if actual <= baseline, savings is 0.0).
    - Explicitly labels all outputs as pre-intervention estimates.

    Args:
        actual_kwh: Actual measured consumption during the period.
        baseline_kwh: Expected normal baseline consumption.
        tariff_rate: Cost per unit in USD. If None, uses resource-calibrated tariff.
        co2_factor: Carbon emission factor in kg CO2 per unit. If None, uses resource default.
        resource_type: 'electricity', 'water', or 'fuel'.

    Returns:
        Structured savings estimate dictionary.

    Raises:
        ValueError: If inputs violate numerical domain constraints.
    """
    res_cfg = RESOURCE_CONFIGS.get(resource_type.lower(), RESOURCE_CONFIGS["electricity"])
    actual_tariff = float(tariff_rate) if tariff_rate is not None else float(res_cfg["default_tariff"])
    actual_co2 = float(co2_factor) if co2_factor is not None else float(res_cfg["default_co2"])

    if actual_tariff <= 0:
        raise ValueError(f"Tariff rate must be positive, got {actual_tariff}.")
    if actual_co2 < 0:
        raise ValueError(f"CO2 emission factor cannot be negative, got {actual_co2}.")
    if actual_kwh < 0 or baseline_kwh < 0:
        raise ValueError(
            f"Consumption values must be non-negative: actual={actual_kwh}, baseline={baseline_kwh}."
        )

    # Calculate excess; prevent negative savings
    excess = max(0.0, float(actual_kwh - baseline_kwh))
    cost_savings = excess * actual_tariff
    co2_avoided = excess * actual_co2

    res_dict: Dict[str, Any] = {
        "resource_type": resource_type.lower(),
        "unit": res_cfg["unit"],
        "excess_consumption": round(excess, 2),
        "cost_savings_usd": round(cost_savings, 2),
        "co2_avoided_kg": round(co2_avoided, 2),
        "tariff_rate_usd_per_unit": actual_tariff,
        "co2_factor_kg_per_unit": actual_co2,
        "is_estimated": True,
        "disclaimer": (
            "Pre-intervention engineering estimate based on baseline delta. "
            "Actual realized savings require post-intervention meter verification."
        ),
    }

    # Backward compatibility keys for electricity
    res_dict["excess_kwh"] = round(excess, 2)
    res_dict["tariff_rate_usd_per_kwh"] = actual_tariff
    res_dict["co2_factor_kg_per_kwh"] = actual_co2

    return res_dict


def evaluate_detection(
    predictions: Union[List[bool], np.ndarray, pd.Series],
    ground_truth: Union[List[bool], np.ndarray, pd.Series],
) -> Dict[str, Any]:
    """
    Evaluates detector performance against ground-truth labels.
    Calculates TP, FP, FN, TN, precision, recall, F1, FPR, accuracy.
    Ground-truth labels are permitted exclusively inside this evaluation function.
    """
    pred_arr = np.array(predictions, dtype=bool)
    truth_arr = np.array(ground_truth, dtype=bool)

    if len(pred_arr) != len(truth_arr):
        raise ValueError(
            f"Length mismatch: predictions has {len(pred_arr)}, ground_truth has {len(truth_arr)}."
        )
    if len(pred_arr) == 0:
        raise ValueError("Cannot evaluate empty prediction/ground_truth arrays.")

    tp = int(np.sum(pred_arr & truth_arr))
    fp = int(np.sum(pred_arr & ~truth_arr))
    fn = int(np.sum(~pred_arr & truth_arr))
    tn = int(np.sum(~pred_arr & ~truth_arr))
    total = len(pred_arr)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    accuracy = (tp + tn) / total if total > 0 else 0.0

    return {
        "total_samples": total,
        "ground_truth_anomalies": int(np.sum(truth_arr)),
        "predicted_anomalies": int(np.sum(pred_arr)),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "false_positive_rate": round(float(fpr), 4),
        "accuracy": round(float(accuracy), 4),
    }

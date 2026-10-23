"""
ResourceShift AI - Test Suite for Multi-Resource Data Generation & Detection
-----------------------------------------------------------------------------
Tests Water and Fuel telemetry generation, multi-resource validation,
resource-calibrated baselines, deterministic anomaly detection, and savings.
"""

from __future__ import annotations

import pandas as pd
import pytest

from backend.app.data.generate_water_data import generate_water_data
from backend.app.data.generate_fuel_data import generate_fuel_data
from backend.app.core.analysis import (
    validate_readings,
    build_baseline,
    detect_anomalies,
    estimate_savings,
    evaluate_detection,
    RESOURCE_CONFIGS,
)


def test_water_generation_shape_and_reproducibility():
    """Verifies that water generator creates 672 rows with 28 anomalous hours."""
    df1 = generate_water_data(seed=42)
    df2 = generate_water_data(seed=42)

    assert len(df1) == 672
    assert df1["resource_type"].unique().tolist() == ["water"]
    assert df1["unit"].unique().tolist() == ["L"]
    assert df1["is_injected_anomaly"].sum() == 28
    pd.testing.assert_frame_equal(df1, df2)


def test_fuel_generation_shape_and_reproducibility():
    """Verifies that fuel generator creates 672 rows with 28 anomalous hours."""
    df1 = generate_fuel_data(seed=42)
    df2 = generate_fuel_data(seed=42)

    assert len(df1) == 672
    assert df1["resource_type"].unique().tolist() == ["fuel"]
    assert df1["unit"].unique().tolist() == ["L"]
    assert df1["is_injected_anomaly"].sum() == 28
    pd.testing.assert_frame_equal(df1, df2)


def test_multi_resource_validation():
    """Tests validation of water and fuel data structures."""
    w_df = generate_water_data(seed=42)
    v_w = validate_readings(w_df, resource_type="water")
    assert len(v_w) == 672
    assert "consumption" in v_w.columns
    assert "hour" in v_w.columns

    # Test invalid resource type
    with pytest.raises(ValueError, match="Invalid resource_type"):
        bad_df = w_df.copy()
        bad_df["resource_type"] = "uranium"
        validate_readings(bad_df)


def test_water_anomaly_detection_benchmark():
    """Verifies 100% precision and recall for water anomaly detection without ground truth."""
    w_df = generate_water_data(seed=42)
    v_w = validate_readings(w_df, resource_type="water")
    baseline = build_baseline(v_w, resource_type="water")
    anomalies = detect_anomalies(v_w, baseline, resource_type="water")

    preds = [False] * len(v_w)
    for a in anomalies:
        preds[a["reading_index"]] = True

    eval_res = evaluate_detection(preds, w_df["is_injected_anomaly"])
    assert eval_res["true_positives"] == 28
    assert eval_res["false_positives"] == 0
    assert eval_res["false_negatives"] == 0
    assert eval_res["precision"] == 1.0
    assert eval_res["recall"] == 1.0
    assert eval_res["false_positive_rate"] == 0.0


def test_fuel_anomaly_detection_benchmark():
    """Verifies 100% precision and recall for fuel anomaly detection without ground truth."""
    f_df = generate_fuel_data(seed=42)
    v_f = validate_readings(f_df, resource_type="fuel")
    baseline = build_baseline(v_f, resource_type="fuel")
    anomalies = detect_anomalies(v_f, baseline, resource_type="fuel")

    preds = [False] * len(f_df)
    for a in anomalies:
        preds[a["reading_index"]] = True

    eval_res = evaluate_detection(preds, f_df["is_injected_anomaly"])
    assert eval_res["true_positives"] == 28
    assert eval_res["false_positives"] == 0
    assert eval_res["false_negatives"] == 0
    assert eval_res["precision"] == 1.0
    assert eval_res["recall"] == 1.0
    assert eval_res["false_positive_rate"] == 0.0


def test_multi_resource_savings_calculations():
    """Tests resource-specific tariff and emission calculations."""
    # Water: 1,000 L excess @ $0.005/L = $5.00, 0.3 kg CO2
    w_sav = estimate_savings(1015.0, 15.0, resource_type="water")
    assert w_sav["excess_consumption"] == 1000.0
    assert w_sav["cost_savings_usd"] == 5.0
    assert w_sav["co2_avoided_kg"] == 0.3
    assert w_sav["unit"] == "L"
    assert w_sav["is_estimated"] is True

    # Fuel: 50 L excess @ $1.15/L = $57.50, 134.0 kg CO2
    f_sav = estimate_savings(51.0, 1.0, resource_type="fuel")
    assert f_sav["excess_consumption"] == 50.0
    assert f_sav["cost_savings_usd"] == 57.5
    assert f_sav["co2_avoided_kg"] == 134.0
    assert f_sav["unit"] == "L"

    # Negative delta clamps to zero
    zero_sav = estimate_savings(10.0, 20.0, resource_type="water")
    assert zero_sav["excess_consumption"] == 0.0
    assert zero_sav["cost_savings_usd"] == 0.0
    assert zero_sav["co2_avoided_kg"] == 0.0

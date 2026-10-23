# ResourceShift AI - Multi-Resource Data Generation & Detection Evaluation

> **Status**: Implemented & Verified across Electricity, Water, and Fuel  
> **Benchmark Datasets**:  
> - Electricity: `data/sample_readings.csv` (672 rows, 50 anomalous hours)  
> - Water: `data/sample_water_readings.csv` (672 rows, 28 anomalous hours)  
> - Fuel: `data/sample_fuel_readings.csv` (672 rows, 28 anomalous hours)  
> **Target Building**: `ENG_HALL_01` (Engineering Hall - North Wing)  

---

## 1. Multi-Resource Telemetry Models

ResourceShift AI standardizes multi-resource monitoring across campus infrastructure using physical units and calibrated baseline properties:

| Resource Type | Internal Unit | Standard Tariff (USD) | Grid / Carbon Factor | Typical Overnight Idle | Daytime Academic Peak |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Electricity** | `kWh` | `$0.14` / kWh | $0.42\text{ kg } CO_2\text{/kWh}$ | 38 – 52 kWh/hr | 180 – 300 kWh/hr |
| **Water** | `L` (Litres) | `$0.005` / L ($5.00/m³) | $0.0003\text{ kg } CO_2\text{/L}$ | 10 – 25 L/hr | 250 – 750 L/hr |
| **Fuel** | `L` (Litres) | `$1.15` / L (Distillate/Oil) | $2.68\text{ kg } CO_2\text{/L}$ | 0.0 – 1.5 L/hr | 15 – 30 L/hr (Warmup) |

---

## 2. Documented Anomaly Scenarios

### Electricity Scenarios (50 Anomalous Hours)
1. **AHU-3 Chiller Override**: Day 3 (21:00 - 03:00, 7 hrs, +115 kWh/hr). Daytime 66°F cooling overnight after maintenance.
2. **Vacuum Furnace Standby**: Day 8 (22:00 - 05:00, 8 hrs, +95 kWh/hr). Materials Lab oven in unmonitored bake cycle.
3. **Auditorium 201 Lighting**: Day 13 (20:00 - 06:00, 11 hrs, +68 kWh/hr). Theatrical spotlights left at 100% capacity.
4. **Cooling Tower Pump Stuck**: Day 17 (23:00 - 06:00, 8 hrs, +85 kWh/hr). Auxiliary pump contactor mechanically stuck closed.
5. **Unmanaged HPC Simulation**: Day 21 (21:00 - 04:00, 8 hrs, +110 kWh/hr). GPU cluster overnight distributed batch render.
6. **Air Compressor Leak**: Day 25 (22:00 - 05:00, 8 hrs, +76 kWh/hr). Pneumatic damper tear cycling compressor at 95%.

### Water Scenarios (28 Anomalous Hours)
1. **Restroom Flushometer Diaphragm Stuck**: Day 4 (22:00 - 05:00, 7 hrs, +350 L/hr). 2nd-floor valve failing to seat.
2. **Irrigation Solenoid Jammed**: Day 10 (21:00 - 04:00, 7 hrs, +550 L/hr). North quad watering zone failing to close.
3. **Chemistry Lab RO Bypass Open**: Day 16 (23:00 - 06:00, 7 hrs, +280 L/hr). Polishing bypass left discharging to drain.
4. **Cooling Tower Makeup Jammed**: Day 23 (22:00 - 05:00, 7 hrs, +480 L/hr). Evaporative pan float jammed below shutoff level.

### Fuel Scenarios (28 Anomalous Hours)
1. **Heating Boiler Burner 2 Stuck**: Day 5 (22:00 - 05:00, 7 hrs, +38 L/hr). Aquastat fault calling for full fire overnight.
2. **Day-Tank Relief Valve Bypass**: Day 11 (23:00 - 06:00, 7 hrs, +26 L/hr). Fuel transfer recirculation pump continuous run.
3. **Weekend Boiler Setback Failure**: Day 18 (21:00 - 04:00, 7 hrs, +42 L/hr). Burners cycling at 80% duty on empty facility.
4. **Generator Fuel Relief Leak**: Day 24 (22:00 - 05:00, 7 hrs, +24 L/hr). Auxiliary fuel line weeping into containment sump.

---

## 3. Comprehensive Multi-Resource Benchmark Results

Evaluated on the 672-hour benchmark dataset for each resource:

| Performance Metric | Electricity (`kWh`) | Water (`L`) | Fuel (`L`) | Unified Total |
| :--- | :--- | :--- | :--- | :--- |
| **Total Samples** | 672 hours | 672 hours | 672 hours | **2,016 hours** |
| **Ground-Truth Anomalies** | 50 hours | 28 hours | 28 hours | **106 hours** |
| **True Positives (TP)** | 50 | 28 | 28 | **106** |
| **False Positives (FP)** | 0 | 0 | 0 | **0** |
| **False Negatives (FN)** | 0 | 0 | 0 | **0** |
| **True Negatives (TN)** | 622 | 644 | 644 | **1,910** |
| **Precision** | **1.0000 (100%)** | **1.0000 (100%)** | **1.0000 (100%)** | **1.0000 (100%)** |
| **Recall** | **1.0000 (100%)** | **1.0000 (100%)** | **1.0000 (100%)** | **1.0000 (100%)** |
| **F1-Score** | **1.0000 (100%)** | **1.0000 (100%)** | **1.0000 (100%)** | **1.0000 (100%)** |
| **False Positive Rate** | **0.0000 (0.0%)** | **0.0000 (0.0%)** | **0.0000 (0.0%)** | **0.0000 (0.0%)** |
| **Total Excess Volume** | 4,451.28 kWh | 11,620.0 L | 910.0 L | — |
| **Recoverable Cost ($)** | **$623.18** | **$58.10** | **$1,046.50** | **$1,727.78** |
| **Abated Carbon ($CO_2$)** | **1,869.54 kg** | **3.49 kg** | **2,438.80 kg** | **4,311.83 kg** |

---

## 4. Methodological Safeguards

1. **Isolation Invariant**: Detection functions never access `is_injected_anomaly`.
2. **Robust Scale (MAD)**: Prevents historical anomalies in training data from contaminating baselines.
3. **Threshold Calibration**:
   - Electricity: $Z \ge 3.0$ and $\Delta\text{kWh} \ge 28.0$
   - Water: $Z \ge 3.0$ and $\Delta\text{L} \ge 100.0$
   - Fuel: $Z \ge 3.0$ and $\Delta\text{L} \ge 10.0$

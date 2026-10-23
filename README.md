# ResourceShift AI

> **Intelligent after-hours resource optimization (Electricity, Water, and Fuel) for campus facilities.**  
> *Built for the GDG Build Beyond AI Hackathon.*

---

## The Problem

University campus buildings consume massive amounts of resources during after-hours periods (nights, weekends, and holidays):
- **Electricity Waste**: Centralized HVAC chillers left running at daytime cooling setpoints on empty floors, auditorium lighting left on overnight, and unthrottled GPU compute clusters.
- **Water Waste**: Restroom flushometer diaphragms stuck open continuously, unmonitored landscape irrigation solenoids, and cooling tower makeup valves jammed below cutoff.
- **Fuel Waste**: Hydronic heating boilers cycling at daytime fire rates during mild autumn nights, and fuel pump bypass loops continuously recirculating.

Because facility managers cannot manually inspect every fixture and meter across campus every night, waste goes unnoticed until utility bills arrive weeks later.

---

## The Solution

**ResourceShift AI** is an agentic resource optimization platform tailored for institutional facilities (targeted at *Engineering Hall – North Wing*):
1. **Multi-Resource Detection (Implemented)**: Evaluates hourly telemetry across **Electricity (`kWh`)**, **Water (`L`)**, and **Fuel (`L`)** against robust baselines (Median + scaled MAD Z-score).
2. **Contextual Investigation via MCP (Implemented)**: Exposes a standardized Model Context Protocol (MCP) server providing 6 diagnostic tools (`get_anomaly`, `check_schedule`, `check_equipment`, `get_resource_history`, `estimate_savings`, `create_proposal`).
3. **AI Cognitive Reasoning via Gemini (Implemented)**: Connects the official Google GenAI SDK to MCP tools to evaluate actual anomaly evidence, diagnose root causes, and propose corrective actions without hallucinating math.
4. **Human-in-the-Loop Protection (Implemented)**: All recommendations require explicit human signoff via `/api/actions/approve` or `/api/actions/reject`. The AI agent **has no actuation credentials and never directly operates hardware**.

---

## Multi-Resource Specifications

| Resource | Internal Unit | Standard Tariff | Emission Factor | Overnight Baseload | Benchmark Anomalies |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Electricity** | `kWh` | `$0.14` / kWh | $0.42\text{ kg } CO_2\text{/kWh}$ | 38 – 52 kWh/hr | 50 hours (6 incidents) |
| **Water** | `L` (Litres) | `$0.005` / L ($5.00/m³) | $0.0003\text{ kg } CO_2\text{/L}$ | 10 – 25 L/hr | 28 hours (4 incidents) |
| **Fuel** | `L` (Litres) | `$1.15` / L (Distillate) | $2.68\text{ kg } CO_2\text{/L}$ | 0.0 – 1.5 L/hr | 28 hours (4 incidents) |

---

## Implementation Status

| Feature / Component | Category | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Project Specification & Rules** | Foundation | **Implemented** | Scope and rules documented in `gemini.md` |
| **Brand & Design Guidelines** | Design System | **Implemented** | Color tokens and layout standards in `brandGuidlines.md` |
| **Architecture Documentation** | Architecture | **Implemented** | System data flow and security rules in `docs/architecture.md` |
| **Multi-Resource Telemetry** | Telemetry | **Implemented & Tested** | 2,016 hourly rows across Electricity, Water, and Fuel |
| **Robust Baseline Modeling** | Analytics | **Implemented & Tested** | Median + scaled MAD grouped by `(is_weekend, hour)` |
| **Deterministic Anomaly Engine** | Analytics | **Implemented & Tested** | $Z \ge 3.0$ and calibrated excess thresholds; 100% precision & recall |
| **Multi-Resource Savings Estimator** | Analytics | **Implemented & Tested** | Deterministic pre-intervention estimates for kWh/L, $, and $CO_2$ |
| **FastAPI Backend REST Service** | Backend API | **Implemented & Tested** | Health, Telemetry, Anomalies, Investigation, and HITL Action endpoints |
| **Human Approval & Audit Trail** | Safety / HITL | **Implemented & Tested** | Immutable audit log in `data/audit_log.json` |
| **FastMCP Python Tool Server** | Agent Protocol | **Implemented & Tested** | 6 investigation & proposal tools in `backend/app/mcp/server.py` |
| **Gemini AI Investigation Engine**| AI / Agent | **Implemented & Tested** | Autonomous root-cause reasoning via MCP tools (`POST /api/investigate`) |
| **No-Actuation Enforcement** | Security | **Implemented & Tested** | Unit-tested prohibition of physical actuators & injection defense |
| **React Operator Dashboard** | Frontend | *Planned* | Modern web dashboard with live charts and approval drawer |
| **Firestore Persistence & Cloud Run**| Cloud | *Planned* | Cloud storage synchronization and container deployment |

---

## Multi-Resource Benchmark Evaluation Results

Evaluated on 2,016 total hours across Electricity, Water, and Fuel:

```
Total Telemetry Samples:        2,016 hours (28 days x 3 resources)
Ground-Truth Anomalies:         106 hours (5.26%)
Ground-Truth Normal:            1,910 hours (94.74%)

Predicted Anomalies:            106 hours
True Positives (TP):            106
False Positives (FP):           0
False Negatives (FN):           0
True Negatives (TN):            1,910

Precision:                      1.0000 (100.0%)
Recall:                         1.0000 (100.0%)
F1-Score:                       1.0000 (100.0%)
False Positive Rate (FPR):      0.0000 (0.0%)
Accuracy:                       1.0000 (100.0%)

Total Excess Electricity Waste: 4,451.28 kWh  -> $623.18  | 1,869.54 kg CO2
Total Excess Water Waste:       11,620.00 L    -> $58.10   |     3.49 kg CO2
Total Excess Fuel Waste:           910.00 L    -> $1,046.50| 2,438.80 kg CO2
Total Recoverable Impact:       $1,727.78 USD  | 4,311.83 kg CO2 abated
```

---

## FastAPI Backend Endpoints

The API runs on port 8000 via Uvicorn (`backend/app/main.py`):

- **`GET /api/health`**: Returns service status, version, and supported resources. Leaks zero secrets or environment variables.
- **`GET /api/telemetry`**: Paginated multi-resource telemetry. Query filters: `resource_type`, `building_id`, `start_time`, `end_time`, `limit`, `offset`.
- **`GET /api/anomalies`**: Returns detected baseline anomalies. Query filters: `resource_type`, `severity` (`low`, `medium`, `high`, `critical`), `building_id`, `limit`.
- **`POST /api/investigate`**: Triggers the Gemini AI investigation agent for an anomaly ID. Gathers evidence via FastMCP tools, diagnoses likely cause, calculates deterministic savings, and creates an advisory proposal. Request: `{"anomaly_id": "...", "context_notes": "..."}`.
- **`POST /api/actions/approve`**: Records human facility manager signoff. Request: `{"proposal_id": "...", "approved_by": "...", "notes": "..."}`. Returns audit entry with `"no_actuation_guarantee": true`.
- **`POST /api/actions/reject`**: Records proposal rejection. Request: `{"proposal_id": "...", "rejected_by": "...", "reason": "..."}`.

---

## Model Context Protocol (MCP) Server

The FastMCP server runs over `stdio` or `sse` transport (`backend/app/mcp/server.py`):

1. **`get_anomaly(anomaly_id: str)`**: Retrieves detailed baseline deviation evidence, timestamp, and context for an anomaly ID.
2. **`check_schedule(building_id: str, timestamp: str)`**: Evaluates whether the facility is scheduled open or closed at a given time.
3. **`check_equipment(equipment_id: str, building_id: str)`**: Retrieves equipment ratings, normal operating hours, and after-hours curtailment policies.
4. **`get_resource_history(resource_type: str, hours: int)`**: Retrieves chronological telemetry for electricity, water, or fuel.
5. **`estimate_savings(resource_type: str, excess_amount: float, duration_hours: float)`**: Deterministically computes cost and carbon savings.
6. **`create_proposal(anomaly_id, resource_type, recommended_action, reason, ...)`**: Creates an advisory recommendation with `status: "pending_review"` and `is_actuated: false`.

---

## Setup & Verification Instructions

### 1. Configure Environment Variables
Set your Google Gemini API key:
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key-here"
$env:GEMINI_MODEL="gemini-1.5-flash"   # or gemini-2.5-flash

# Linux / macOS
export GEMINI_API_KEY="your-gemini-api-key-here"
export GEMINI_MODEL="gemini-1.5-flash"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate All Synthetic Datasets (Electricity, Water, Fuel)
```bash
python backend/app/data/generate_data.py --output data/sample_readings.csv
python backend/app/data/generate_water_data.py --output data/sample_water_readings.csv
python backend/app/data/generate_fuel_data.py --output data/sample_fuel_readings.csv
```

### 4. Run the Complete Test Suite
```bash
pytest -v
```
*(Runs 49 comprehensive tests covering multi-resource generation, anomaly detection, FastAPI endpoints, FastMCP tools, Gemini investigation workflows, prompt-injection defense, and no-actuation security.)*

### 5. Start the FastAPI Backend Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### 6. Start the FastMCP Server
```bash
python backend/mcp_server.py
```
*(Runs over stdio transport by default, ready for LLM agent integration.)*

---

## Workspace Structure

```
ResourceShift-AI/
├── .env.example                    # Template for environment variables (no secrets)
├── .gitignore                      # Git exclusion rules for Python, Node, and secrets
├── brandGuidlines.md               # Visual style guide, accessible color tokens & layout
├── docs/
│   ├── architecture.md             # Multi-resource architecture & system data flow
│   ├── data-and-evaluation.md      # Generation methodologies, scenarios & verified metrics
│   └── security.md                 # Input validation, no-actuation rules & audit trail
├── gemini.md                       # Project context, coding rules, HITL principles & roadmap
├── pytest.ini                      # Pytest configuration with pythonpath = .
├── requirements.txt                # Core dependencies (pandas, numpy, fastapi, uvicorn, mcp, google-genai, pytest)
├── README.md                       # Complete documentation, schemas, commands & evaluation
├── data/
│   ├── sample_readings.csv         # 672-hour electricity dataset
│   ├── sample_water_readings.csv   # 672-hour water dataset
│   ├── sample_fuel_readings.csv    # 672-hour fuel dataset
│   ├── audit_log.json              # Local persistent audit trail
│   └── proposals.json              # Action proposal store
└── backend/
    ├── mcp_server.py               # Standalone MCP server CLI entrypoint
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                 # FastAPI application with 6 REST endpoints
    │   ├── agent/
    │   │   ├── __init__.py
    │   │   └── investigator.py     # Gemini AI investigation engine with MCP tool calling
    │   ├── data/
    │   │   ├── __init__.py
    │   │   ├── generate_data.py    # Electricity generator
    │   │   ├── generate_water_data.py # Water generator
    │   │   └── generate_fuel_data.py  # Fuel generator
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── analysis.py         # Multi-resource validation, baseline, detection & savings
    │   │   ├── audit.py            # Proposal store & immutable audit logger
    │   │   └── telemetry_store.py  # Multi-resource loader, query & anomaly cache
    │   └── mcp/
    │       ├── __init__.py
    │       └── server.py           # FastMCP server with 6 investigation tools
    └── tests/
        ├── __init__.py
        ├── test_analysis.py        # Task 1 electricity benchmark tests (21 tests)
        ├── test_multi_resource.py  # Multi-resource validation & benchmark tests (6 tests)
        ├── test_api.py             # FastAPI endpoint and audit trail tests (6 tests)
        ├── test_mcp_server.py      # MCP server tools and safety invariant tests (8 tests)
        └── test_agent.py           # Gemini AI investigation workflow & security tests (8 tests)
```

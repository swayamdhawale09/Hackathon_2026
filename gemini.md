# ResourceShift AI - Gemini Assistant Context & Project Guide

> **Hackathon**: GDG Build Beyond AI  
> **Target Window**: ~2.5 Hours Incremental Build  
> **Core Role**: Energy Optimization & Human-in-the-Loop Waste Mitigation Agent  

---

## 1. Project Context & Mission

**ResourceShift AI** is an intelligent energy operations assistant purpose-built for university campus facilities. It monitors power telemetry in a single college building (e.g., Engineering Hall), identifies after-hours electricity waste (such as HVAC systems left running on empty floors, forgotten classroom lighting, or idle server/lab equipment), investigates root causes, proposes corrective shifts for facility manager approval, and estimates kilowatt-hour (kWh), financial ($), and carbon ($CO_2$) savings.

---

## 2. Core Architecture Principles

1. **Separation of Computation and Reasoning**:
   - **Python performs calculations**: Baseline energy curves, standard deviations, statistical anomaly detection (Z-score/thresholds), kWh delta calculations, monetary cost math, and carbon offset formulas are strictly calculated in deterministic Python code.
   - **Gemini handles reasoning**: Investigates root causes by correlating telemetry anomalies with contextual data (class schedules, building operating hours, ambient weather, historical precedents) and formulates human-readable explanations and prioritized recommendations.
   - *Rule*: Never prompt Gemini to compute raw mathematical operations or statistical baselines that Python can deterministically calculate.

2. **Strict Human-in-the-Loop (HITL) Safety Guardrail**:
   - The agent is an **advisor**, not an actuator.
   - The agent proposes specific, actionable recommendations (e.g., *"Set 3rd Floor HVAC to setback mode (74°F) from 20:00 to 06:00"*).
   - The agent **must never directly actuate or control physical building hardware**. A certified facility manager or operator must review, approve, modify, or reject every action through the dashboard.

3. **Decoupled Modular Design**:
   - Every module (telemetry generator, anomaly engine, MCP tools, Gemini orchestrator, REST API, React UI) must have standalone utility and clear interface boundaries.

---

## 3. Technology Stack

- **Frontend**: React (Vite) + Tailwind CSS + Lucide Icons + Recharts
- **Backend API**: Python 3.11+ + FastAPI + Pydantic v2
- **Agent Reasoning**: Google Gemini API (`gemini-1.5-flash` or `gemini-1.5-pro` with structured outputs / tool calling)
- **Tool Protocol**: Lightweight Python Model Context Protocol (MCP) server
- **Persistence**: Google Firebase Firestore (Telemetry logs, anomaly events, action proposals, audit logs)
- **Deployment**: Google Cloud Run (containerized microservice)

---

## 4. Coding & Quality Rules

### Python (Backend, MCP & Analysis Engine)
- Use standard Python 3.11+ idioms with strict type annotations (`typing`).
- Validate all incoming and outgoing payloads with **Pydantic v2** models.
- Keep business logic pure and unit-testable (e.g., anomaly math decoupled from database I/O).
- Graceful degradation: If Gemini API is unreachable, the system must still display deterministic anomalies and raw estimated savings without crashing.

### Frontend (React & Tailwind CSS)
- Adhere strictly to [brandGuidlines.md](file:///c:/Users/SWAYAM%20DHAWALE/Desktop/ResourceShift-AI/brandGuidlines.md) for color tokens, typography, and component hierarchy.
- Use functional components with hooks (`useState`, `useEffect`, `useMemo`).
- Provide intuitive loading, empty, and error states for all asynchronous operations.
- Clearly present confidence scores and cost estimations alongside each proposed action.

---

## 5. Security & Safety Requirements

1. **Zero Secret Leaks**:
   - No API keys, credentials, or private project IDs committed to git.
   - Read secrets strictly from environment variables via `.env`.
2. **Audit Logging**:
   - Every proposed action, human approval, or rejection must be immutably recorded in the audit log with a timestamp and user identifier.
3. **Fail-Safe Operation**:
   - If telemetry data is stale or corrupted, flag the data quality rather than triggering spurious alert cascades.

---

## 6. Incremental Implementation Workflow (Hackathon Roadmap)

Given the ~2.5-hour hackathon timeframe, development proceeds through targeted, verified phases:

- [x] **Phase 1: Project Blueprint & Foundation** *(Current)*
  - Establish `gemini.md`, `brandGuidlines.md`, `README.md`, `.gitignore`, `.env.example`, and `docs/architecture.md`.
  - Validate Git hygiene and repo state.
- [x] **Phase 2: Synthetic Telemetry & Deterministic Anomaly Engine** *(Completed)*
  - Implement realistic building load generator (28 days = 672 hourly rows, 6 documented anomalies).
  - Implement deterministic threshold and robust statistical anomaly detection algorithms (MAD + Z-score) with 21 unit & integration tests.
- [x] **Phase 3: Multi-Resource Backend API & FastMCP Tool Server** *(Completed)*
  - Multi-resource support for Electricity (kWh), Water (L), and Fuel (L) with 2,016 hourly records and 106 detected anomalies.
  - FastAPI server with /api/health, /api/telemetry, /api/anomalies, /api/actions/approve, and /api/actions/reject.
  - FastMCP tool server exposing 6 investigative tools (get_anomaly, check_schedule, check_equipment, get_resource_history, estimate_savings, create_proposal).
  - 41 passing unit, integration, and security tests.
- [x] **Phase 4: Gemini Cognitive Reasoning Layer** *(Completed)*
  - Integrated official Google Gemini Python SDK (google-genai / google-generativeai) with gemini-1.5-flash / gemini-2.5-flash.
  - Autonomous root-cause investigation workflow connected to FastMCP diagnostic tools.
  - Structured investigation reports with deterministic savings enforcement, adversarial prompt injection defense, and proposal registration.
  - Added POST /api/investigate endpoint with 49 total passing unit, integration, and security tests.
- [ ] **Phase 5: React Operator Dashboard**
  - Real-time telemetry visualization, KPI cards (kWh wasted, potential $ saved), Anomaly Alert feed, and HITL Action Approval center.
- [ ] **Phase 6: Persistence & Cloud Readiness**
  - Firestore syncing for persistence and Cloud Run containerization check.

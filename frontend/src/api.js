/**
 * ResourceShift AI - API Client
 * Connects frontend to the FastAPI backend endpoints.
 */

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchTelemetry(resourceType = null, limit = 168) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (resourceType) params.append('resource_type', resourceType);
  const res = await fetch(`${API_BASE}/telemetry?${params.toString()}`);
  if (!res.ok) throw new Error(`Telemetry fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchAnomalies(resourceType = null, severity = null, limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (resourceType) params.append('resource_type', resourceType);
  if (severity) params.append('severity', severity);
  const res = await fetch(`${API_BASE}/anomalies?${params.toString()}`);
  if (!res.ok) throw new Error(`Anomalies fetch failed: ${res.statusText}`);
  return res.json();
}

export async function investigateAnomaly(anomalyId, contextNotes = '') {
  const res = await fetch(`${API_BASE}/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anomaly_id: anomalyId,
      context_notes: contextNotes,
    }),
  });

  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    const err = new Error(data.detail || `Investigation failed (${res.status})`);
    err.status = res.status;
    err.detail = data.detail;
    throw err;
  }
  return data;
}

export async function approveAction(proposalId, approvedBy = 'facility_manager', notes = '') {
  const res = await fetch(`${API_BASE}/actions/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      proposal_id: proposalId,
      approved_by: approvedBy,
      notes: notes,
    }),
  });

  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    const err = new Error(data.detail || `Approval failed (${res.status})`);
    err.status = res.status;
    err.detail = data.detail;
    throw err;
  }
  return data;
}

export async function rejectAction(proposalId, rejectedBy = 'facility_manager', reason = '') {
  const res = await fetch(`${API_BASE}/actions/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      proposal_id: proposalId,
      rejected_by: rejectedBy,
      reason: reason || 'Dismissed by facility operator',
    }),
  });

  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    const err = new Error(data.detail || `Rejection failed (${res.status})`);
    err.status = res.status;
    err.detail = data.detail;
    throw err;
  }
  return data;
}

export async function fetchAuditTrail() {
  const res = await fetch(`${API_BASE}/audit`);
  if (!res.ok) throw new Error(`Audit fetch failed: ${res.statusText}`);
  return res.json();
}

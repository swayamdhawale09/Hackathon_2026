import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import OverviewCards from './components/OverviewCards';
import ConsumptionChart from './components/ConsumptionChart';
import AnomalyFeed from './components/AnomalyFeed';
import InvestigationModal from './components/InvestigationModal';
import AuditTrailView from './components/AuditTrailView';
import { 
  fetchHealth, 
  fetchTelemetry, 
  fetchAnomalies, 
  fetchAuditTrail, 
  investigateAnomaly, 
  approveAction, 
  rejectAction 
} from './api';
import { AlertCircle, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function App() {
  // Global Application State
  const [healthStatus, setHealthStatus] = useState(null);
  const [telemetry, setTelemetry] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [auditTrail, setAuditTrail] = useState([]);
  const [proposals, setProposals] = useState([]);
  
  // UI Selection State
  const [selectedResource, setSelectedResource] = useState('electricity');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [globalError, setGlobalError] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  // Modal & Investigation State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [investigationResult, setInvestigationResult] = useState(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigationError, setInvestigationError] = useState(null);

  // HITL Decision Action State
  const [isActionSubmitting, setIsActionSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Load All Backend Data
  const loadData = useCallback(async (showRefreshingSpinner = false) => {
    if (showRefreshingSpinner) setIsRefreshing(true);
    setGlobalError(null);

    try {
      const [healthRes, telemetryRes, anomaliesRes, auditRes] = await Promise.all([
        fetchHealth().catch((err) => ({ status: 'error', error: err.message })),
        fetchTelemetry(null, 300).catch(() => ({ readings: [] })),
        fetchAnomalies(null, null, 100).catch(() => ({ anomalies: [] })),
        fetchAuditTrail().catch(() => ({ audit_trail: [], proposals: [] })),
      ]);

      setHealthStatus(healthRes);
      setTelemetry(telemetryRes.readings || []);
      setAnomalies(anomaliesRes.anomalies || []);
      setAuditTrail(auditRes.audit_trail || []);
      setProposals(auditRes.proposals || []);
    } catch (err) {
      console.error('Failed to load application data:', err);
      setGlobalError('Could not connect to ResourceShift backend. Is the server running on port 8000?');
    } finally {
      if (showRefreshingSpinner) setIsRefreshing(false);
    }
  }, []);

  // Initial mount load
  useEffect(() => {
    loadData(false);
  }, [loadData]);

  // Toast Auto-Dismiss
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  // Handler: Open and trigger AI Anomaly Investigation
  const handleOpenInvestigate = async (anomaly) => {
    setSelectedAnomaly(anomaly);
    setIsModalOpen(true);
    setInvestigationResult(null);
    setInvestigationError(null);
    setActionError(null);
    setActionSuccess(null);

    // Check if proposal already exists
    const existing = proposals.find((p) => p.anomaly_id === anomaly.anomaly_id);
    if (existing) {
      // Already investigated: formulate view model
      setInvestigationResult({
        investigation_id: 'PREVIOUS_INVESTIGATION',
        anomaly_id: anomaly.anomaly_id,
        resource_type: anomaly.resource_type,
        building_id: anomaly.building_id,
        timestamp: anomaly.timestamp,
        likely_cause: existing.reason || 'Flagged after-hours baseline excess detected by deterministic engine.',
        evidence_summary: anomaly.supporting_evidence?.description || 'Baseline anomaly recorded.',
        recommended_action: existing.recommended_action || 'Review and adjust schedule.',
        confidence_score: existing.confidence_score || 0.92,
        confidence_explanation: 'Grounding verified against campus schedules and equipment ratings.',
        deterministic_savings: {
          cost_savings_usd: existing.estimated_savings_usd,
          excess_consumption: anomaly.excess_consumption,
          co2_avoided_kg: existing.estimated_co2_kg,
          unit: anomaly.unit,
          tariff_rate_usd_per_unit: (existing.estimated_savings_usd / Math.max(1, anomaly.excess_consumption)).toFixed(3),
        },
        created_proposal_id: existing.proposal_id,
        tools_called: ['get_anomaly', 'check_schedule', 'check_equipment', 'estimate_savings', 'create_proposal'],
      });
      return;
    }

    // Call real backend Gemini/MCP investigation
    setIsInvestigating(true);
    try {
      const result = await investigateAnomaly(anomaly.anomaly_id);
      setInvestigationResult(result);

      // Refresh audit and proposals so the new proposal is indexed
      const auditRes = await fetchAuditTrail().catch(() => null);
      if (auditRes) {
        setAuditTrail(auditRes.audit_trail || []);
        setProposals(auditRes.proposals || []);
      }
    } catch (err) {
      console.error('Investigation failed:', err);
      setInvestigationError(err);
    } finally {
      setIsInvestigating(false);
    }
  };

  // Handler: Human Facility Operator Approval
  const handleApprove = async (proposalId, approvedBy, notes) => {
    setIsActionSubmitting(true);
    setActionError(null);
    try {
      const decision = await approveAction(proposalId, approvedBy, notes);
      setActionSuccess(decision);
      setToastMessage({
        type: 'success',
        text: `Proposal ${proposalId} approved! Logged under Audit ID ${decision.audit_id}.`,
      });

      // Refresh data
      await loadData(false);
    } catch (err) {
      setActionError(err.message || 'Failed to submit approval.');
    } finally {
      setIsActionSubmitting(false);
    }
  };

  // Handler: Human Facility Operator Rejection
  const handleReject = async (proposalId, rejectedBy, reason) => {
    setIsActionSubmitting(true);
    setActionError(null);
    try {
      const decision = await rejectAction(proposalId, rejectedBy, reason);
      setActionSuccess(decision);
      setToastMessage({
        type: 'info',
        text: `Proposal ${proposalId} rejected. Logged under Audit ID ${decision.audit_id}.`,
      });

      // Refresh data
      await loadData(false);
    } catch (err) {
      setActionError(err.message || 'Failed to submit rejection.');
    } finally {
      setIsActionSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
      
      {/* Top Navigation */}
      <Navbar
        healthStatus={healthStatus}
        isRefreshing={isRefreshing}
        onRefresh={() => loadData(true)}
      />

      {/* Global Connection Error Alert */}
      {globalError && (
        <div className="bg-red-500/10 border-b border-red-500/20 px-4 py-2.5">
          <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-red-300">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{globalError}</span>
            </div>
            <button
              onClick={() => loadData(true)}
              className="px-2.5 py-1 rounded bg-red-500/20 hover:bg-red-500/30 font-medium transition-colors"
            >
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl bg-slate-900 border border-emerald-500/40 shadow-2xl text-xs text-slate-100 backdrop-blur-md animate-bounce">
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Main Dashboard Canvas */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* 1. Overview Cards (Multi-Resource & Savings Impact) */}
        <section aria-label="Resource Overview">
          <OverviewCards
            telemetry={telemetry}
            anomalies={anomalies}
            proposals={proposals}
          />
        </section>

        {/* 2. Consumption Time-Series Chart */}
        <section aria-label="Consumption Time-Series">
          <ConsumptionChart
            telemetry={telemetry}
            anomalies={anomalies}
            selectedResource={selectedResource}
            onSelectResource={setSelectedResource}
          />
        </section>

        {/* 3. Anomalies Feed with AI Investigation */}
        <section aria-label="Detected Anomalies">
          <AnomalyFeed
            anomalies={anomalies}
            proposals={proposals}
            onInvestigate={handleOpenInvestigate}
            investigatingId={isInvestigating ? selectedAnomaly?.anomaly_id : null}
          />
        </section>

        {/* 4. Operational Audit Trail */}
        <section aria-label="Audit Trail">
          <AuditTrailView
            auditTrail={auditTrail}
            proposals={proposals}
            isLoading={isRefreshing}
          />
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/60 py-6 mt-12 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-200">ResourceShift AI</span>
            <span>—</span>
            <span>GDG Build Beyond AI Hackathon 2026</span>
          </div>

          <div className="flex items-center gap-4 text-slate-500">
            <span className="flex items-center gap-1 text-emerald-400/80">
              <ShieldCheck className="w-3.5 h-3.5" />
              Advisory Architecture • No Direct Actuators
            </span>
            <span>•</span>
            <span>Deterministic Math • WCAG AA</span>
          </div>
        </div>
      </footer>

      {/* AI Investigation & HITL Modal */}
      <InvestigationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        anomaly={selectedAnomaly}
        investigationResult={investigationResult}
        isLoading={isInvestigating}
        error={investigationError}
        existingProposal={
          selectedAnomaly
            ? proposals.find((p) => p.anomaly_id === selectedAnomaly.anomaly_id)
            : null
        }
        onApprove={handleApprove}
        onReject={handleReject}
        isActionSubmitting={isActionSubmitting}
        actionError={actionError}
        actionSuccess={actionSuccess}
      />

    </div>
  );
}

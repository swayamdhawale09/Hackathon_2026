import React, { useState } from 'react';
import { 
  X, 
  Sparkles, 
  CheckCircle2, 
  XCircle, 
  ShieldCheck, 
  DollarSign, 
  Cpu, 
  Key, 
  Terminal, 
  AlertCircle
} from 'lucide-react';

export default function InvestigationModal({
  isOpen,
  onClose,
  anomaly,
  investigationResult,
  isLoading,
  error,
  existingProposal,
  onApprove,
  onReject,
  isActionSubmitting,
  actionError,
  actionSuccess,
}) {
  const [operatorName, setOperatorName] = useState('facility_manager');
  const [notesOrReason, setNotesOrReason] = useState('');

  if (!isOpen || !anomaly) return null;

  // Determine current proposal (either passed from parent or returned from investigation)
  const proposalId = investigationResult?.created_proposal_id || existingProposal?.proposal_id;
  const currentStatus = actionSuccess?.status || existingProposal?.status || (investigationResult ? 'pending_review' : null);

  // Check if error is missing Gemini API key
  const isKeyError = error && (
    error.status === 503 || 
    (error.message && error.message.toLowerCase().includes('gemini_api_key')) ||
    (error.detail && error.detail.toLowerCase().includes('gemini_api_key'))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-3xl rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl overflow-hidden my-8 z-10 max-h-[90vh] flex flex-col">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 border border-emerald-500/30 text-emerald-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  AI Anomaly Investigation
                </h3>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  {anomaly.anomaly_id}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Google Gemini reasoning grounded in FastMCP deterministic telemetry & equipment tools.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 space-y-6 overflow-y-auto">

          {/* Anomaly Context Summary Banner */}
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Resource</span>
              <span className="font-semibold text-slate-200 capitalize font-mono mt-0.5 block">
                {anomaly.resource_type} ({anomaly.unit})
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Timestamp</span>
              <span className="font-semibold text-slate-200 font-mono mt-0.5 block">
                {anomaly.timestamp}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Baseline Delta</span>
              <span className="font-bold text-amber-400 font-mono mt-0.5 block">
                +{anomaly.excess_consumption.toFixed(1)} {anomaly.unit}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Severity</span>
              <span className="font-bold text-slate-200 uppercase font-mono mt-0.5 block">
                {anomaly.severity}
              </span>
            </div>
          </div>

          {/* 1. Loading State */}
          {isLoading && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin" />
                <Sparkles className="w-5 h-5 text-emerald-400 absolute inset-0 m-auto animate-pulse" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-200">Executing Multi-Step AI Workflow...</h4>
                <p className="text-xs text-slate-400 mt-1 max-w-md">
                  Connecting to FastMCP diagnostic tools, querying schedule & equipment databases, and applying Gemini reasoning.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                <span>Tools: get_anomaly</span>
                <span>•</span>
                <span>check_schedule</span>
                <span>•</span>
                <span>check_equipment</span>
                <span>•</span>
                <span>estimate_savings</span>
              </div>
            </div>
          )}

          {/* 2. Configuration Error State (Missing Gemini API Key) */}
          {error && (
            <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-5 space-y-3">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 shrink-0">
                  <Key className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-amber-300">
                    {isKeyError ? 'Gemini API Credentials Required' : 'Investigation Workflow Error'}
                  </h4>
                  <p className="text-xs text-amber-200/90 mt-1">
                    {error.message || error.detail || 'Failed to complete autonomous investigation.'}
                  </p>
                </div>
              </div>

              {isKeyError && (
                <div className="mt-3 p-3 rounded-lg bg-slate-950/80 border border-amber-500/20 text-xs font-mono text-slate-300 space-y-2">
                  <div className="text-amber-400 font-semibold flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5" />
                    <span>How to configure the real Gemini model:</span>
                  </div>
                  <p className="text-slate-400 font-sans">
                    ResourceShift AI strictly enforces real Gemini reasoning and rejects fake AI mocks. Set your API key in the terminal before running the backend:
                  </p>
                  <div className="bg-slate-900 p-2 rounded border border-slate-800 text-emerald-400 select-all">
                    set GEMINI_API_KEY=your_gemini_api_key_here
                  </div>
                  <p className="text-[11px] text-slate-500 font-sans">
                    PowerShell: <code>$env:GEMINI_API_KEY="your_key"</code> | Linux/Mac: <code>export GEMINI_API_KEY="your_key"</code>
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 3. Investigation Results */}
          {investigationResult && (
            <div className="space-y-6">
              
              {/* Root Cause & Evidence */}
              <div className="rounded-xl bg-slate-800/60 border border-slate-700/60 p-5 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5" />
                      Gemini Root Cause Analysis
                    </span>
                    <h4 className="text-base font-semibold text-slate-100 mt-1">
                      {investigationResult.likely_cause}
                    </h4>
                  </div>

                  {/* Confidence meter */}
                  <div className="text-right shrink-0">
                    <div className="text-xs text-slate-400 font-medium">Confidence</div>
                    <div className="text-lg font-mono font-bold text-emerald-400">
                      {Math.round(investigationResult.confidence_score * 100)}%
                    </div>
                  </div>
                </div>

                <div className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-700/40">
                  <span className="font-semibold text-slate-200 block mb-1">Diagnostic Evidence:</span>
                  {investigationResult.evidence_summary}
                </div>

                {/* Tools invoked */}
                {investigationResult.tools_called?.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap text-[11px] text-slate-400">
                    <span className="text-slate-500">MCP Diagnostic Tools Executed:</span>
                    {investigationResult.tools_called.map((tool) => (
                      <span key={tool} className="px-2 py-0.5 rounded bg-slate-700/60 text-slate-300 font-mono">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Deterministic Savings Box */}
              {investigationResult.deterministic_savings && (
                <div className="rounded-xl bg-gradient-to-br from-emerald-950/30 to-slate-800/60 border border-emerald-500/30 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                      <DollarSign className="w-3.5 h-3.5" />
                      Deterministic Savings Estimate
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                      Zero-Hallucination Math
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                    <div className="p-3 rounded-lg bg-slate-900/60 border border-emerald-500/20">
                      <span className="text-[11px] text-slate-400 block">Cost Reduction</span>
                      <span className="text-xl font-mono font-bold text-emerald-400 mt-0.5 block">
                        ${investigationResult.deterministic_savings.cost_savings_usd?.toFixed(2)}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        @ ${investigationResult.deterministic_savings.tariff_rate_usd_per_unit}/unit
                      </span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-emerald-500/20">
                      <span className="text-[11px] text-slate-400 block">Resource Recovered</span>
                      <span className="text-xl font-mono font-bold text-slate-100 mt-0.5 block">
                        {investigationResult.deterministic_savings.excess_consumption?.toFixed(1)}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          {investigationResult.deterministic_savings.unit}
                        </span>
                      </span>
                      <span className="text-[10px] text-slate-500">Calculated baseline delta</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-emerald-500/20">
                      <span className="text-[11px] text-slate-400 block">Carbon Abatement</span>
                      <span className="text-xl font-mono font-bold text-teal-300 mt-0.5 block">
                        {investigationResult.deterministic_savings.co2_avoided_kg?.toFixed(1)}{' '}
                        <span className="text-xs font-normal text-slate-400">kg CO2</span>
                      </span>
                      <span className="text-[10px] text-slate-500">Scope 2 emissions</span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 italic">
                    {investigationResult.deterministic_savings.disclaimer || 
                      'Pre-intervention engineering estimate based on baseline delta. Actual realized savings require post-intervention meter verification.'}
                  </p>
                </div>
              )}

              {/* Recommended Action & Human Approval */}
              <div className="rounded-xl bg-slate-800/80 border border-slate-700 p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      Human-in-the-Loop Advisory Proposal
                    </span>
                    <h4 className="text-base font-bold text-slate-100 mt-1">
                      {investigationResult.recommended_action}
                    </h4>
                  </div>
                  {proposalId && (
                    <span className="text-xs font-mono text-slate-400 bg-slate-900 px-2 py-1 rounded border border-slate-700">
                      {proposalId}
                    </span>
                  )}
                </div>

                {/* Decision Status Banner if already decided */}
                {currentStatus === 'approved' && (
                  <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <div>
                        <span className="font-bold">Recommendation Approved:</span> Shift logged for facility operations follow-up.
                      </div>
                    </div>
                    <span className="font-mono text-[11px] text-emerald-400">
                      {actionSuccess?.audit_id || 'Recorded in Audit Log'}
                    </span>
                  </div>
                )}

                {currentStatus === 'rejected' && (
                  <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                      <div>
                        <span className="font-bold">Recommendation Rejected:</span> Dismissal recorded with facility justification.
                      </div>
                    </div>
                    <span className="font-mono text-[11px] text-red-400">
                      {actionSuccess?.audit_id || 'Recorded in Audit Log'}
                    </span>
                  </div>
                )}

                {/* Interactive Controls (Visible when pending review) */}
                {currentStatus === 'pending_review' && (
                  <div className="space-y-3 pt-2">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">
                          Facility Operator Name
                        </label>
                        <input
                          type="text"
                          value={operatorName}
                          onChange={(e) => setOperatorName(e.target.value)}
                          placeholder="facility_manager"
                          className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">
                          Operator Notes / Justification
                        </label>
                        <input
                          type="text"
                          value={notesOrReason}
                          onChange={(e) => setNotesOrReason(e.target.value)}
                          placeholder="e.g. Schedule verified; manual setback authorized"
                          className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        />
                      </div>
                    </div>

                    {actionError && (
                      <div className="text-xs text-red-400 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5" />
                        <span>Action error: {actionError}</span>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                      <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Advisory only: Never actuates physical equipment automatically.</span>
                      </div>

                      <div className="flex items-center gap-2">
                        {/* Reject Button */}
                        <button
                          type="button"
                          disabled={isActionSubmitting || !proposalId}
                          onClick={() => onReject(proposalId, operatorName, notesOrReason)}
                          className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 active:bg-slate-700 text-red-400 hover:text-red-300 border border-red-500/30 text-xs font-semibold transition-colors disabled:opacity-50"
                        >
                          Reject Proposal
                        </button>

                        {/* Approve Button */}
                        <button
                          type="button"
                          disabled={isActionSubmitting || !proposalId}
                          onClick={() => onApprove(proposalId, operatorName, notesOrReason)}
                          className="px-5 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:from-emerald-700 text-white text-xs font-semibold shadow-md shadow-emerald-950/40 border border-emerald-400/30 transition-all disabled:opacity-50 flex items-center gap-1.5"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          <span>{isActionSubmitting ? 'Recording...' : 'Approve Shift'}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}

              </div>

            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Facility Operations Audit Logging Enabled</span>
          </div>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}

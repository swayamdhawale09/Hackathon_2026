import React from 'react';
import { 
  History, 
  CheckCircle2, 
  XCircle, 
  ShieldCheck, 
  UserCheck, 
  Clock, 
  FileCheck
} from 'lucide-react';

export default function AuditTrailView({ 
  auditTrail = [], 
  proposals = [],
  isLoading 
}) {
  // Map proposal info by proposal_id for enriched metadata
  const proposalMap = new Map();
  proposals.forEach((p) => {
    proposalMap.set(p.proposal_id, p);
  });

  return (
    <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-5 shadow-sm">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-700/60">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <History className="w-4 h-4 text-emerald-400" />
            Operational Audit Trail
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographically tracked record of facility manager approvals, rejections, and zero-actuation guarantees.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Non-Actuating Safety Policy</span>
          </span>
          <span className="text-xs font-mono font-semibold px-2 py-1 rounded bg-slate-700 text-slate-300">
            {auditTrail.length} Events
          </span>
        </div>
      </div>

      {/* Audit Log Content */}
      <div className="mt-4">
        {isLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">
            Loading audit records...
          </div>
        ) : auditTrail.length === 0 ? (
          <div className="py-10 text-center text-slate-400 flex flex-col items-center">
            <FileCheck className="w-8 h-8 text-slate-600 mb-2" />
            <p className="text-sm font-medium text-slate-300">No decisions recorded yet.</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              Use "Investigate with AI" on any detected anomaly above, then submit an Approve or Reject decision to generate audit trail entries.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-700/80 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-2.5 px-3">Audit ID</th>
                  <th className="py-2.5 px-3">Decision</th>
                  <th className="py-2.5 px-3">Proposal ID</th>
                  <th className="py-2.5 px-3">Action Details</th>
                  <th className="py-2.5 px-3">Actor</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Safety Policy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {auditTrail.slice().reverse().map((entry) => {
                  const isApproved = entry.decision === 'approved';
                  const prop = proposalMap.get(entry.proposal_id);

                  return (
                    <tr key={entry.audit_id} className="hover:bg-slate-750/50 transition-colors">
                      {/* Audit ID */}
                      <td className="py-3 px-3 font-mono font-semibold text-slate-300">
                        {entry.audit_id}
                      </td>

                      {/* Decision Badge */}
                      <td className="py-3 px-3">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-semibold uppercase text-[10px] tracking-wide border ${
                          isApproved
                            ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                            : 'bg-red-500/15 border-red-500/30 text-red-300'
                        }`}>
                          {isApproved ? (
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <XCircle className="w-3 h-3 text-red-400" />
                          )}
                          {entry.decision}
                        </span>
                      </td>

                      {/* Proposal ID */}
                      <td className="py-3 px-3 font-mono text-slate-400">
                        {entry.proposal_id}
                      </td>

                      {/* Action Details / Notes */}
                      <td className="py-3 px-3 text-slate-200 max-w-xs">
                        <div className="font-medium text-slate-100 truncate">
                          {prop?.recommended_action || 'Advisory Shift Proposal'}
                        </div>
                        {entry.notes_or_reason && (
                          <div className="text-[11px] text-slate-400 italic truncate mt-0.5">
                            "{entry.notes_or_reason}"
                          </div>
                        )}
                      </td>

                      {/* Actor */}
                      <td className="py-3 px-3 text-slate-300 flex items-center gap-1.5 pt-4">
                        <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-medium">{entry.actor}</span>
                      </td>

                      {/* Timestamp */}
                      <td className="py-3 px-3 font-mono text-slate-400 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-500" />
                          <span>{entry.timestamp?.slice(0, 19).replace('T', ' ')}</span>
                        </div>
                      </td>

                      {/* Safety Guarantee */}
                      <td className="py-3 px-3">
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400/90 font-medium">
                          <ShieldCheck className="w-3 h-3 text-emerald-400" />
                          <span>Advisory Only (No Actuation)</span>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}

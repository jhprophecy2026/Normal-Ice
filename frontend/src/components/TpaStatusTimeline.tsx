/**
 * TpaStatusTimeline — Healthcare RCM Dashboard
 *
 * Exports:
 *   TpaStatusBadge     — compact pill for list / table views
 *   TpaStatusTimeline  — vertical 4-node stepper with embedded TPA reply card
 */

import { useState } from 'react';
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, Clock } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

export type TpaStatusType =
  | 'approved'
  | 'paid'
  | 'pending'
  | 'submitted'
  | 'query'
  | 'rejected'
  | 'denied'
  | 'draft';

export interface TpaReply {
  /** Current TPA decision for this step */
  status: TpaStatusType;
  /** Amount the TPA has approved */
  approved_amount?: number | null;
  /** Original billed / claimed amount */
  billed_amount?: number | null;
  /** TPA remarks or query text */
  remarks?: string | null;
  /** Reason for deduction / rejection */
  deduction_reason?: string | null;
  /** ISO timestamp of TPA response */
  timestamp?: string | null;
  /** TPA-side reference / auth number */
  tpa_reference?: string | null;
}

export interface TpaTimeline {
  /**
   * The step the case is currently on.
   * 1 = Pre-Auth  2 = Enhancement  3 = Discharge  4 = Settlement
   */
  current_step: 1 | 2 | 3 | 4;
  pre_auth?: TpaReply | null;
  enhancement?: TpaReply | null;
  discharge?: TpaReply | null;
  settlement?: TpaReply | null;
}

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  TpaStatusType,
  { label: string; dot: string; pill: string; cardAccent: string }
> = {
  approved:  {
    label: 'Approved',
    dot:  'bg-emerald-500',
    pill: 'bg-emerald-50 dark:bg-emerald-900/25 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-200 dark:ring-emerald-800',
    cardAccent: 'border-l-emerald-400 dark:border-l-emerald-600',
  },
  paid:      {
    label: 'Paid',
    dot:  'bg-emerald-500',
    pill: 'bg-emerald-50 dark:bg-emerald-900/25 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-200 dark:ring-emerald-800',
    cardAccent: 'border-l-emerald-400 dark:border-l-emerald-600',
  },
  pending:   {
    label: 'Pending',
    dot:  'bg-amber-400',
    pill: 'bg-amber-50 dark:bg-amber-900/25 text-amber-700 dark:text-amber-300 ring-1 ring-amber-200 dark:ring-amber-800',
    cardAccent: 'border-l-amber-400 dark:border-l-amber-600',
  },
  submitted: {
    label: 'Submitted',
    dot:  'bg-blue-500',
    pill: 'bg-blue-50 dark:bg-blue-900/25 text-blue-700 dark:text-blue-300 ring-1 ring-blue-200 dark:ring-blue-800',
    cardAccent: 'border-l-blue-400 dark:border-l-blue-600',
  },
  query:     {
    label: 'Query Raised',
    dot:  'bg-amber-400',
    pill: 'bg-amber-50 dark:bg-amber-900/25 text-amber-700 dark:text-amber-300 ring-1 ring-amber-200 dark:ring-amber-800',
    cardAccent: 'border-l-amber-400 dark:border-l-amber-600',
  },
  rejected:  {
    label: 'Rejected',
    dot:  'bg-red-500',
    pill: 'bg-red-50 dark:bg-red-900/25 text-red-700 dark:text-red-300 ring-1 ring-red-200 dark:ring-red-800',
    cardAccent: 'border-l-red-400 dark:border-l-red-600',
  },
  denied:    {
    label: 'Denied',
    dot:  'bg-red-500',
    pill: 'bg-red-50 dark:bg-red-900/25 text-red-700 dark:text-red-300 ring-1 ring-red-200 dark:ring-red-800',
    cardAccent: 'border-l-red-400 dark:border-l-red-600',
  },
  draft:     {
    label: 'Draft',
    dot:  'bg-slate-400',
    pill: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 ring-1 ring-slate-200 dark:ring-slate-700',
    cardAccent: 'border-l-slate-300 dark:border-l-slate-600',
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function inr(val?: number | null) {
  if (val == null) return '—';
  return `₹${Number(val).toLocaleString('en-IN')}`;
}

function fmtTimestamp(ts?: string | null) {
  if (!ts) return null;
  try {
    return new Date(ts).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

// ─── Status Badge (List View) ─────────────────────────────────────────────────

export function TpaStatusBadge({ status }: { status: TpaStatusType }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${cfg.pill}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

// ─── TPA Reply Card ───────────────────────────────────────────────────────────

function TpaReplyCard({ reply, stepLabel }: { reply: TpaReply; stepLabel: string }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUS_CONFIG[reply.status] ?? STATUS_CONFIG.draft;
  const remark = reply.remarks || reply.deduction_reason;
  const isLongRemark = (remark?.length ?? 0) > 110;

  const deduction =
    reply.billed_amount != null && reply.approved_amount != null
      ? reply.billed_amount - reply.approved_amount
      : null;

  return (
    <div
      className={`
        mt-2.5 rounded-r-xl border-l-[3px] ${cfg.cardAccent}
        bg-white dark:bg-slate-900/80
        border border-l-0 border-slate-100 dark:border-slate-800
        px-4 py-3.5 space-y-3
      `}
    >
      {/* ── Status row ── */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <TpaStatusBadge status={reply.status} />
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-200 truncate">
            {stepLabel} {cfg.label}
          </span>
        </div>
        {reply.tpa_reference && (
          <span className="font-mono text-[10px] text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md">
            Ref: {reply.tpa_reference}
          </span>
        )}
      </div>

      {/* ── Financials ── */}
      {(reply.approved_amount != null || reply.billed_amount != null) && (
        <div className="flex items-stretch gap-0 divide-x divide-slate-100 dark:divide-slate-800">
          {reply.approved_amount != null && (
            <div className="pr-4">
              <p className="text-[10px] font-medium text-slate-400 uppercase tracking-widest mb-0.5">
                Approved
              </p>
              <p className="text-[17px] font-bold text-emerald-600 dark:text-emerald-400 leading-none">
                {inr(reply.approved_amount)}
              </p>
            </div>
          )}
          {reply.billed_amount != null && (
            <div className="px-4">
              <p className="text-[10px] font-medium text-slate-400 uppercase tracking-widest mb-0.5">
                Billed
              </p>
              <p className="text-[17px] font-semibold text-slate-500 dark:text-slate-400 leading-none">
                {inr(reply.billed_amount)}
              </p>
            </div>
          )}
          {deduction != null && deduction !== 0 && (
            <div className="pl-4">
              <p className="text-[10px] font-medium text-slate-400 uppercase tracking-widest mb-0.5">
                {deduction > 0 ? 'Deducted' : 'Extra'}
              </p>
              <p className={`text-[17px] font-bold leading-none ${
                deduction > 0
                  ? 'text-red-500 dark:text-red-400'
                  : 'text-emerald-600 dark:text-emerald-400'
              }`}>
                {deduction > 0 ? '−' : '+'}{inr(Math.abs(deduction))}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Remarks / deduction reason ── */}
      {remark && (
        <div>
          <p className={`text-xs text-slate-500 dark:text-slate-400 leading-relaxed ${
            !expanded && isLongRemark ? 'line-clamp-2' : ''
          }`}>
            {remark}
          </p>
          {isLongRemark && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="mt-1 inline-flex items-center gap-0.5 text-[11px] font-semibold text-blue-500 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
            >
              {expanded
                ? <><ChevronUp size={11} /> Show less</>
                : <><ChevronDown size={11} /> Read more</>
              }
            </button>
          )}
        </div>
      )}

      {/* ── Timestamp ── */}
      {reply.timestamp && (
        <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
          <Clock size={10} />
          {fmtTimestamp(reply.timestamp)}
        </div>
      )}
    </div>
  );
}

// ─── Node icon ────────────────────────────────────────────────────────────────

type NodeState = 'done' | 'active' | 'pending';

function NodeDot({ state, status }: { state: NodeState; status?: TpaStatusType }) {
  if (state === 'done') {
    if (status === 'rejected' || status === 'denied') {
      return (
        <div className="w-7 h-7 rounded-full bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
          <XCircle size={16} className="text-red-500 dark:text-red-400" />
        </div>
      );
    }
    return (
      <div className="w-7 h-7 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
        <CheckCircle2 size={16} className="text-blue-600 dark:text-blue-400" />
      </div>
    );
  }

  if (state === 'active') {
    return (
      <div className="relative w-7 h-7 flex items-center justify-center">
        <span className="absolute inline-flex w-full h-full rounded-full bg-blue-400/30 animate-ping" />
        <span className="relative w-3.5 h-3.5 rounded-full bg-blue-600 dark:bg-blue-500 ring-2 ring-white dark:ring-slate-950" />
      </div>
    );
  }

  return (
    <div className="w-7 h-7 flex items-center justify-center">
      <span className="w-3 h-3 rounded-full border-2 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-950" />
    </div>
  );
}

// ─── Timeline ─────────────────────────────────────────────────────────────────

const STEPS: { id: 1 | 2 | 3 | 4; label: string; key: keyof Omit<TpaTimeline, 'current_step'> }[] = [
  { id: 1, label: 'Pre-Authorization', key: 'pre_auth' },
  { id: 2, label: 'Enhancement',       key: 'enhancement' },
  { id: 3, label: 'Discharge',         key: 'discharge' },
  { id: 4, label: 'Settlement',        key: 'settlement' },
];

interface TpaStatusTimelineProps {
  tpaResponse: TpaTimeline;
}

export default function TpaStatusTimeline({ tpaResponse }: TpaStatusTimelineProps) {
  const { current_step } = tpaResponse;

  return (
    <div className="w-full">
      {STEPS.map((step, idx) => {
        const isLast = idx === STEPS.length - 1;
        const state: NodeState =
          step.id < current_step ? 'done' :
          step.id === current_step ? 'active' :
          'pending';
        const reply = tpaResponse[step.key] as TpaReply | null | undefined;

        return (
          <div key={step.id} className="flex gap-3">
            {/* ── Left column: dot + connector ── */}
            <div className="flex flex-col items-center" style={{ width: 28 }}>
              <NodeDot state={state} status={reply?.status} />
              {!isLast && (
                <div
                  className={`w-px flex-1 mt-1 mb-0.5 ${
                    step.id < current_step
                      ? 'bg-blue-200 dark:bg-blue-800/60'
                      : 'bg-slate-200 dark:bg-slate-800'
                  }`}
                  style={{ minHeight: 20 }}
                />
              )}
            </div>

            {/* ── Right column: label + card ── */}
            <div className={`flex-1 min-w-0 ${isLast ? 'pb-0' : 'pb-5'}`}>
              {/* Step header */}
              <div className="flex items-center gap-2 h-7 flex-wrap">
                <span className={`text-sm font-semibold leading-none ${
                  state === 'active'
                    ? 'text-slate-900 dark:text-white'
                    : state === 'done'
                    ? 'text-slate-500 dark:text-slate-400'
                    : 'text-slate-400 dark:text-slate-600'
                }`}>
                  {step.label}
                </span>

                {/* Completed: show badge inline */}
                {state === 'done' && reply && (
                  <TpaStatusBadge status={reply.status} />
                )}

                {/* Completed: show approved amount inline if no card visible */}
                {state === 'done' && reply?.approved_amount != null && (
                  <span className="ml-auto text-xs font-semibold text-slate-400 dark:text-slate-500">
                    {inr(reply.approved_amount)}
                  </span>
                )}

                {/* Pending: muted label */}
                {state === 'pending' && (
                  <span className="text-xs text-slate-400 dark:text-slate-600">—</span>
                )}
              </div>

              {/* Active step reply card */}
              {state === 'active' && reply && (
                <TpaReplyCard reply={reply} stepLabel={step.label} />
              )}

              {/* Active step with no reply yet */}
              {state === 'active' && !reply && (
                <p className="mt-1.5 text-xs text-slate-400 dark:text-slate-500">
                  Awaiting TPA response…
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

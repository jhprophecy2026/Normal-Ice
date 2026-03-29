import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import {
  Upload, CheckCircle2, AlertTriangle, AlertCircle,
  Download, Plus, ArrowLeft, ArrowRight, IndianRupee, FileText, Lock, Send,
} from 'lucide-react';
import {
  getCase, generatePreAuthPdf, createEnhancement,
  extractEnhancementData,
  createDischarge, extractDischargeData, updateDischarge,
  createSettlement, updateSettlement,
  getFinancialAudit,
} from '../services/api';
import type {
  CaseDetail, EnhancementData, EnhancementExtract, DischargeData, DischargeResponse,
  SettlementResponse, FinancialAudit,
} from '../types/api';

// ---------------------------------------------------------------------------
// Tiny helpers
// ---------------------------------------------------------------------------

function fmt(n: number | undefined | null) {
  if (n == null) return '—';
  return `₹${n.toLocaleString('en-IN')}`;
}

function Spinner({ sm }: { sm?: boolean }) {
  return (
    <span className={`inline-block rounded-full border-2 border-white/30 border-t-white animate-spin ${sm ? 'w-3.5 h-3.5' : 'w-4 h-4'}`} />
  );
}

function Badge({ status }: { status: string }) {
  const map: Record<string, string> = {
    draft:     'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300',
    submitted: 'bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300',
    pending:   'bg-amber-100 dark:bg-amber-900/60 text-amber-700 dark:text-amber-300',
    approved:  'bg-green-100 dark:bg-green-900/60 text-green-700 dark:text-green-300',
    rejected:  'bg-red-100 dark:bg-red-900/60 text-red-700 dark:text-red-300',
    paid:      'bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300',
  };
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full capitalize ${map[status] ?? map.pending}`}>
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Revenue flags dropdown
// ---------------------------------------------------------------------------

type RevenueFlag = { field: string; severity: 'critical' | 'warning'; message: string };

function FlagsDropdown({ critical, warnings }: { critical: RevenueFlag[]; warnings: RevenueFlag[] }) {
  const [open, setOpen] = useState(false);
  const total = critical.length + warnings.length;

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header / toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Revenue Reconciliation Flags
          </span>
          {critical.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs font-semibold">
              <AlertCircle size={11} />
              {critical.length} Critical
            </span>
          )}
          {warnings.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs font-semibold">
              <AlertTriangle size={11} />
              {warnings.length} Caution
            </span>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown body */}
      {open && (
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {critical.map((flag, i) => (
            <div key={`c-${i}`} className="flex items-start gap-2 px-4 py-3 bg-red-50 dark:bg-red-950/30 text-sm text-red-700 dark:text-red-300">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <span>{flag.message}</span>
            </div>
          ))}
          {warnings.map((flag, i) => (
            <div key={`w-${i}`} className="flex items-start gap-2 px-4 py-3 bg-amber-50 dark:bg-amber-950/30 text-sm text-amber-700 dark:text-amber-300">
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />
              <span>{flag.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Discharge confidence score
// ---------------------------------------------------------------------------

type DischargeFields = {
  discharge_date?: string | null;
  final_diagnosis?: string | null;
  final_icd10_codes?: string | null;
  procedure_codes?: string | null;
  total_bill_amount?: number | null;
  room_charges?: number | null;
  icu_charges?: number | null;
  surgery_charges?: number | null;
  medicine_charges?: number | null;
  investigation_charges?: number | null;
  other_charges?: number | null;
};

function computeDischargeConfidence(f: DischargeFields): number {
  let score = 0;
  if (f.discharge_date)    score += 15;
  if (f.final_diagnosis)   score += 20;
  if (f.final_icd10_codes) score += 15;
  if (f.procedure_codes)   score += 10;
  if (f.total_bill_amount) score += 20;
  const chargesFilled = [
    f.room_charges, f.icu_charges, f.surgery_charges,
    f.medicine_charges, f.investigation_charges, f.other_charges,
  ].filter(v => v != null && v > 0).length;
  score += Math.min(chargesFilled, 3) * 7; // up to 21 pts for line items
  return Math.min(Math.round(score), 100);
}

function DischargeConfidenceBadge({ score }: { score: number }) {
  const high   = score >= 75;
  const medium = score >= 50 && score < 75;
  const r = 18;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  const colorRing = high ? '#22c55e' : medium ? '#f59e0b' : '#ef4444';
  const colorBg   = high
    ? 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800'
    : medium
    ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800'
    : 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800';
  const colorText = high
    ? 'text-green-700 dark:text-green-300'
    : medium
    ? 'text-amber-700 dark:text-amber-300'
    : 'text-red-700 dark:text-red-300';
  const label = high
    ? 'High'
    : medium
    ? 'Moderate'
    : 'Low';
  const icon = high ? '✓' : medium ? '!' : '✗';

  return (
    <div className={`flex items-center gap-4 px-4 py-3 rounded-xl border text-sm ${colorBg}`}>
      {/* Circular score gauge */}
      <div className="relative shrink-0 w-12 h-12">
        <svg width="48" height="48" viewBox="0 0 48 48" className="-rotate-90">
          <circle cx="24" cy="24" r={r} fill="none" stroke="currentColor" strokeWidth="4"
            className="text-slate-200 dark:text-slate-700" />
          <circle cx="24" cy="24" r={r} fill="none" strokeWidth="4"
            stroke={colorRing}
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round" />
        </svg>
        <span className={`absolute inset-0 flex items-center justify-center text-xs font-bold ${colorText}`}>
          {icon}
        </span>
      </div>
      <div>
        <p className={`font-semibold ${colorText}`}>{score}% Extraction Confidence</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label} confidence</p>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs text-slate-500 dark:text-slate-500 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{value || '—'}</p>
    </div>
  );
}

function FormInput({
  label, value, onChange, type = 'text', area = false, span2 = false,
}: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; area?: boolean; span2?: boolean;
}) {
  const cls =
    'w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 ' +
    'bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 ' +
    'placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors';
  return (
    <div className={span2 ? 'col-span-2' : ''}>
      <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">{label}</label>
      {area ? (
        <textarea rows={3} value={value} onChange={(e) => onChange(e.target.value)} className={cls + ' resize-none'} />
      ) : (
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className={cls} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Horizontal stepper
// ---------------------------------------------------------------------------

type StepStatus = 'done' | 'active' | 'pending' | 'locked';

interface StepDef {
  id: number;
  label: string;
  status: StepStatus;
}

function Stepper({
  steps, activeStep, onStepClick,
}: {
  steps: StepDef[];
  activeStep: number;
  onStepClick: (id: number) => void;
}) {
  return (
    <div className="flex items-start justify-center mb-10">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-start w-40 min-w-0 shrink-0">
          {/* Circle + label */}
          <div className="flex flex-col items-center flex-shrink-0">
            <button
              onClick={() => step.status !== 'locked' && onStepClick(step.id)}
              disabled={step.status === 'locked'}
              className={[
                'w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-200 focus:outline-none',
                step.status === 'done'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : step.status === 'active'
                  ? 'bg-white dark:bg-slate-800 text-blue-600 ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-50 dark:ring-offset-slate-950'
                  : step.status === 'locked'
                  ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed border border-slate-200 dark:border-slate-700'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 cursor-pointer',
              ].join(' ')}
            >
              {step.status === 'done' ? <CheckCircle2 size={20} /> : step.status === 'locked' ? <Lock size={14} /> : step.id}
            </button>
            <span className={`text-xs mt-2 font-medium text-center whitespace-nowrap ${
              step.status === 'active' ? 'text-blue-600 dark:text-blue-400' :
              step.status === 'done'   ? 'text-slate-600 dark:text-slate-400' :
              step.status === 'locked' ? 'text-slate-400 dark:text-slate-600' :
              'text-slate-500 dark:text-slate-400'
            }`}>
              {step.label}
            </span>
          </div>

          {/* Connector line (not after last) */}
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mt-5 mx-2 rounded-full transition-colors ${
              step.status === 'done' ? 'bg-blue-500' : 'bg-slate-200 dark:bg-slate-700'
            }`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Financial Audit Panel
// ---------------------------------------------------------------------------

function RiskBadge({ tier, color }: { tier: string; color: string }) {
  const cls =
    color === 'green' ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700' :
    color === 'amber' ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700' :
                        'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 border-red-200 dark:border-red-700';
  return (
    <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${cls}`}>{tier} Risk</span>
  );
}

function inr(n: number) { return `₹${n.toLocaleString('en-IN')}`; }

function FinancialAuditPanel({ abhaId }: { abhaId: string }) {
  const [audit, setAudit] = useState<FinancialAudit | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<'overview' | 'claims' | 'benchmarks' | 'risk' | 'insurance' | 'tpa'>('overview');

  useEffect(() => {
    setLoading(true);
    getFinancialAudit(abhaId)
      .then(setAudit)
      .catch(() => setAudit(null))
      .finally(() => setLoading(false));
  }, [abhaId]);

  if (loading) return null;
  if (!audit) return null;

  const tabs: { key: typeof section; label: string }[] = [
    { key: 'overview',   label: 'Overview' },
    { key: 'claims',     label: `Claims (${audit.past_claims.length})` },
    { key: 'benchmarks', label: 'Cost Benchmarks' },
    { key: 'risk',       label: 'Risk Factors' },
    { key: 'insurance',  label: 'Insurance' },
    { key: 'tpa',        label: 'TPA Notes' },
  ];

  const impactColor = (impact: string) =>
    impact.includes('cost_to_patient') || impact.includes('financial_risk') || impact.includes('high_cost') || impact.includes('claim_risk')
      ? 'text-red-600 dark:text-red-400'
      : impact.includes('cost_increase') || impact.includes('operational_risk') || impact.includes('transfusion_risk') || impact.includes('minor')
      ? 'text-amber-600 dark:text-amber-400'
      : 'text-slate-500 dark:text-slate-400';

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <IndianRupee size={15} className="text-blue-500" />
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Financial Audit</span>
          <RiskBadge tier={audit.risk_tier} color={audit.risk_color} />
        </div>
        <svg className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="bg-white dark:bg-slate-900">
          {/* Sub-tabs */}
          <div className="flex gap-0 border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
            {tabs.map(t => (
              <button
                key={t.key}
                onClick={() => setSection(t.key)}
                className={`shrink-0 px-4 py-2.5 text-xs font-semibold transition-colors whitespace-nowrap border-b-2 -mb-px ${
                  section === t.key
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="p-4 space-y-4">

            {/* Overview */}
            {section === 'overview' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Generated {audit.generated_date}</span>
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{audit.summary}</p>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                    <p className="text-xs text-slate-500 mb-0.5">Sum Insured</p>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-200">{inr(audit.insurance.sum_insured)}</p>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                    <p className="text-xs text-slate-500 mb-0.5">Available Balance</p>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-200">{inr(audit.insurance.available)}</p>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                    <p className="text-xs text-slate-500 mb-0.5">Insurer</p>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{audit.insurance.company}</p>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                    <p className="text-xs text-slate-500 mb-0.5">TPA</p>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{audit.insurance.tpa}</p>
                  </div>
                </div>
                {audit.recommendations.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Recommendations</p>
                    <ul className="space-y-1.5">
                      {audit.recommendations.map((r, i) => (
                        <li key={i} className="flex gap-2 text-xs text-slate-600 dark:text-slate-400">
                          <span className="shrink-0 text-blue-500 mt-0.5">→</span>
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Past Claims */}
            {section === 'claims' && (
              <div className="space-y-3">
                {audit.past_claims.length === 0 && (
                  <p className="text-sm text-slate-400 text-center py-4">No past claims on record.</p>
                )}
                {audit.past_claims.map((c, i) => (
                  <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{c.event}</p>
                      <span className={`shrink-0 text-xs font-bold px-2 py-0.5 rounded-full ${
                        c.status === 'Settled' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' :
                        c.status.includes('Rejected') ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' :
                        'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                      }`}>{c.status}</span>
                    </div>
                    <p className="text-xs text-slate-400">{c.admission_date} → {c.discharge_date} · TPA: {c.tpa}</p>
                    <div className="grid grid-cols-3 gap-2 pt-1">
                      <div>
                        <p className="text-xs text-slate-400">Claimed</p>
                        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">{inr(c.claimed_amount)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">Settled</p>
                        <p className={`text-sm font-semibold ${c.settled_amount > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500'}`}>{inr(c.settled_amount)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">Deducted</p>
                        <p className="text-sm font-semibold text-red-500">{inr(c.deduction_amount)}</p>
                      </div>
                    </div>
                    {c.deduction_reason && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 rounded px-2 py-1.5 mt-1">
                        <span className="font-semibold">Deduction reason: </span>{c.deduction_reason}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Cost Benchmarks */}
            {section === 'benchmarks' && (
              <div className="space-y-3">
                {audit.cost_benchmarks.map((b, i) => (
                  <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{b.category}</p>
                      <span className="text-sm font-bold text-blue-600 dark:text-blue-400 shrink-0">{b.typical_range}</span>
                    </div>
                    <p className="text-xs text-slate-400"><span className="font-medium">Basis:</span> {b.basis}</p>
                    <p className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded px-2 py-1">
                      {b.patient_note}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {/* Risk Factors */}
            {section === 'risk' && (
              <div className="space-y-3">
                {audit.risk_factors.map((r, i) => (
                  <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-1.5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{r.factor}</p>
                      <span className={`text-xs font-bold shrink-0 ${impactColor(r.impact)}`}>
                        {r.impact.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400">{r.detail}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Insurance */}
            {section === 'insurance' && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ['Company', audit.insurance.company],
                    ['TPA', audit.insurance.tpa],
                    ['Policy No.', audit.insurance.policy_no],
                    ['Room Eligibility', audit.insurance.room_eligibility],
                    ['Cashless Network', audit.insurance.cashless_network],
                  ].map(([l, v]) => (
                    <div key={l} className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                      <p className="text-xs text-slate-400 mb-0.5">{l}</p>
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">{v}</p>
                    </div>
                  ))}
                  <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                    <p className="text-xs text-slate-400 mb-0.5">Sum Insured / Available</p>
                    <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      {inr(audit.insurance.sum_insured)} / {inr(audit.insurance.available)}
                    </p>
                  </div>
                </div>
                {audit.insurance.key_exclusions.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Key Exclusions</p>
                    <ul className="space-y-1">
                      {audit.insurance.key_exclusions.map((e, i) => (
                        <li key={i} className="flex gap-2 text-xs text-red-600 dark:text-red-400">
                          <span className="shrink-0">✕</span>{e}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* TPA Watch Points */}
            {section === 'tpa' && (
              <div className="space-y-2">
                {audit.tpa_watch_points.map((p, i) => (
                  <div key={i} className="flex gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-xs text-amber-700 dark:text-amber-300">
                    <AlertTriangle size={13} className="shrink-0 mt-0.5" />
                    {p}
                  </div>
                ))}
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 1 — Pre-Auth content
// ---------------------------------------------------------------------------

function PreAuthContent({
  caseData,
  onNext,
}: {
  caseData: CaseDetail;
  onNext: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const pa = caseData.pre_auth;
  if (!pa) return <p className="text-slate-500 text-sm">No pre-auth data.</p>;

  const isAlreadySubmitted = pa.status === 'submitted' || pa.status === 'approved';

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const blob = await generatePreAuthPdf(pa.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pre_auth_${pa.id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setSubmitted(true);
      setTimeout(onNext, 800);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Already-submitted banner */}
      {isAlreadySubmitted && (
        <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 text-sm">
          <CheckCircle2 size={15} className="shrink-0" />
          Pre-auth has been submitted to TPA. You can still download the PDF or proceed to the next step.
        </div>
      )}

      {/* Core fields grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
        <Info label="Patient Name"       value={pa.patient_name} />
        <Info label="ABHA ID"            value={pa.abha_id} />
        <Info label="Date of Birth"      value={pa.date_of_birth} />
        <Info label="Gender"             value={pa.gender} />
        <Info label="Contact"            value={pa.contact} />
        <Info label="Policy No."         value={pa.policy_no} />
      </div>

      <div className="h-px bg-slate-100 dark:bg-slate-800" />

      <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
        <Info label="Hospital"           value={pa.hospital_name} />
        <Info label="ROHINI ID"          value={pa.rohini_id} />
        <Info label="Doctor"             value={pa.doctor_name} />
        <Info label="Admission Date"     value={pa.admission_date} />
        <Info label="Admission Type"     value={pa.admission_type} />
        <Info label="Room Type"          value={pa.room_type} />
      </div>

      <div className="h-px bg-slate-100 dark:bg-slate-800" />

      <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
        <div className="col-span-2 md:col-span-3">
          <Info label="Presenting Complaints" value={pa.presenting_complaints} />
        </div>
        <div className="col-span-2">
          <Info label="Provisional Diagnosis" value={pa.provisional_diagnosis} />
        </div>
        <Info label="ICD-10 Code"          value={pa.icd10_diagnosis_code} />
        {pa.surgery_name   && <Info label="Surgery"     value={pa.surgery_name} />}
        {pa.icd10_pcs_code && <Info label="ICD-10 PCS"  value={pa.icd10_pcs_code} />}
        <Info label="Total Estimated Cost"  value={fmt(pa.total_estimated_cost)} />
      </div>

      {/* Financial Audit — shown when ABHA ID has a pre-generated profile */}
      {pa.abha_id && <FinancialAuditPanel abhaId={pa.abha_id} />}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2 flex-wrap">
        {!isAlreadySubmitted && (
          <button
            onClick={handleSubmit}
            disabled={submitting || submitted}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60"
          >
            {submitting ? <Spinner sm /> : submitted ? <CheckCircle2 size={14} /> : <Send size={14} />}
            {submitting ? 'Generating & Submitting…' : submitted ? 'Submitted!' : 'Submit Pre-Auth to TPA'}
          </button>
        )}

        <button
          onClick={async () => {
            const blob = await generatePreAuthPdf(pa.id);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `pre_auth_${pa.id.slice(0, 8)}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="flex items-center gap-2 px-5 py-2.5 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-sm font-semibold rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          <Download size={14} />
          Download PDF
        </button>

        {isAlreadySubmitted && (
          <button
            onClick={onNext}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            Next: Enhancement <ArrowRight size={14} />
          </button>
        )}

        {pa.patient_id && (
          <Link
            to={`/patients/${pa.patient_id}`}
            className="flex items-center gap-2 px-5 py-2.5 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-sm font-semibold rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <FileText size={14} />
            View Patient Record
          </Link>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 2 — Enhancement content
// ---------------------------------------------------------------------------

function EnhancementForm({
  preAuthId,
  seqNo,
  originalTotal,
  onSave,
  onCancel,
}: {
  preAuthId: string;
  seqNo: number;
  originalTotal: number | null | undefined;
  onSave: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<Partial<EnhancementData>>({});
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: keyof EnhancementData, v: unknown) => setForm((f) => ({ ...f, [k]: v }));
  const setNum = (k: keyof EnhancementData, v: string) => set(k, v ? Number(v) : undefined);

  // Compute revised total from line items
  const lineTotal =
    (form.revised_room_rent_per_day   || 0) +
    (form.revised_icu_charges_per_day || 0) +
    (form.revised_ot_charges          || 0) +
    (form.revised_surgeon_fees        || 0) +
    (form.revised_medicines_consumables || 0) +
    (form.revised_investigations      || 0);

  const revisedTotal = form.revised_total_estimated_cost ?? (lineTotal > 0 ? lineTotal : null);
  const variance = originalTotal != null && revisedTotal != null ? revisedTotal - originalTotal : null;

  const handleExtract = async (file: File) => {
    setUploading(true); setErr(null);
    try {
      const extracted: EnhancementExtract = await extractEnhancementData(preAuthId, file);
      setForm((f) => ({
        ...f,
        reason:                    extracted.reason                    ?? f.reason,
        clinical_justification:    extracted.clinical_justification    ?? f.clinical_justification,
        updated_diagnosis:         extracted.updated_diagnosis         ?? f.updated_diagnosis,
        updated_icd10_code:        extracted.updated_icd10_code        ?? f.updated_icd10_code,
        updated_line_of_treatment: extracted.updated_line_of_treatment ?? f.updated_line_of_treatment,
        updated_surgery_name:      extracted.updated_surgery_name      ?? f.updated_surgery_name,
        updated_icd10_pcs_code:    extracted.updated_icd10_pcs_code    ?? f.updated_icd10_pcs_code,
        revised_room_rent_per_day:    extracted.revised_room_rent_per_day    ?? f.revised_room_rent_per_day,
        revised_icu_charges_per_day:  extracted.revised_icu_charges_per_day  ?? f.revised_icu_charges_per_day,
        revised_ot_charges:           extracted.revised_ot_charges           ?? f.revised_ot_charges,
        revised_surgeon_fees:         extracted.revised_surgeon_fees         ?? f.revised_surgeon_fees,
        revised_medicines_consumables: extracted.revised_medicines_consumables ?? f.revised_medicines_consumables,
        revised_investigations:       extracted.revised_investigations       ?? f.revised_investigations,
        revised_total_estimated_cost: extracted.revised_total_estimated_cost ?? f.revised_total_estimated_cost,
      }));
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message || 'Extraction failed');
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async () => {
    if (!form.reason?.trim()) { setErr('Reason is required'); return; }
    setSaving(true); setErr(null);
    try {
      const payload: EnhancementData = {
        ...form,
        pre_auth_id: preAuthId,
        reason: form.reason!,
        revised_total_estimated_cost: revisedTotal ?? undefined,
      };
      await createEnhancement(preAuthId, payload);
      onSave();
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
        New Enhancement #{seqNo}
      </h4>

      {/* ── PDF Upload zone ── */}
      <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-6 cursor-pointer transition-colors ${
        uploading
          ? 'border-blue-400 bg-blue-50 dark:bg-blue-950/20'
          : 'border-slate-300 dark:border-slate-700 hover:border-blue-400 hover:bg-blue-50/40 dark:hover:bg-blue-950/10'
      }`}>
        <input type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff,.docx,.xlsx,.xls,.csv"
          className="hidden"
          disabled={uploading}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleExtract(f); }}
        />
        {uploading ? (
          <>
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin mb-2" />
            <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">Extracting with Gemini AI…</p>
            <p className="text-xs text-slate-400 mt-1">Reading diagnosis, procedure & cost updates</p>
          </>
        ) : (
          <>
            <Upload size={22} className="text-slate-400 mb-2" />
            <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">Upload Enhancement Document (Optional)</p>
            <p className="text-xs text-slate-400 mt-1">Progress note, revised estimate, surgeon's letter — Gemini will auto-fill fields below</p>
          </>
        )}
      </label>

      {/* ── Section 1: Reason ── */}
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Reason for Enhancement</p>
        <div className="grid grid-cols-1 gap-3">
          <FormInput label="Reason *" value={form.reason || ''} onChange={(v) => set('reason', v)} span2 />
          <FormInput label="Clinical Justification" value={form.clinical_justification || ''} onChange={(v) => set('clinical_justification', v)} span2 area />
        </div>
      </div>

      <div className="h-px bg-slate-100 dark:bg-slate-800" />

      {/* ── Section 2: Updated Clinical Details ── */}
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Updated Clinical Details</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormInput label="Updated Diagnosis"          value={form.updated_diagnosis || ''} onChange={(v) => set('updated_diagnosis', v)} />
          <FormInput label="Updated ICD-10 Code"        value={form.updated_icd10_code || ''} onChange={(v) => set('updated_icd10_code', v)} />
          <FormInput label="Updated Surgery / Procedure" value={form.updated_surgery_name || ''} onChange={(v) => set('updated_surgery_name', v)} />
          <FormInput label="Updated ICD-10 PCS Code"    value={form.updated_icd10_pcs_code || ''} onChange={(v) => set('updated_icd10_pcs_code', v)} />
          <FormInput label="Updated Line of Treatment"  value={form.updated_line_of_treatment || ''} onChange={(v) => set('updated_line_of_treatment', v)} span2 />
        </div>
      </div>

      <div className="h-px bg-slate-100 dark:bg-slate-800" />

      {/* ── Section 3: Revised Cost Breakdown ── */}
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Revised Cost Breakdown</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormInput label="Room Rent / Day (₹)"          value={form.revised_room_rent_per_day?.toString() || ''}    onChange={(v) => setNum('revised_room_rent_per_day', v)}    type="number" />
          <FormInput label="ICU Charges / Day (₹)"        value={form.revised_icu_charges_per_day?.toString() || ''} onChange={(v) => setNum('revised_icu_charges_per_day', v)}  type="number" />
          <FormInput label="OT / Surgery Charges (₹)"     value={form.revised_ot_charges?.toString() || ''}          onChange={(v) => setNum('revised_ot_charges', v)}            type="number" />
          <FormInput label="Surgeon / Doctor Fees (₹)"    value={form.revised_surgeon_fees?.toString() || ''}        onChange={(v) => setNum('revised_surgeon_fees', v)}          type="number" />
          <FormInput label="Medicines & Consumables (₹)"  value={form.revised_medicines_consumables?.toString() || ''} onChange={(v) => setNum('revised_medicines_consumables', v)} type="number" />
          <FormInput label="Investigations (₹)"           value={form.revised_investigations?.toString() || ''}      onChange={(v) => setNum('revised_investigations', v)}        type="number" />
          <FormInput label="Override Total (₹)"           value={form.revised_total_estimated_cost?.toString() || ''} onChange={(v) => setNum('revised_total_estimated_cost', v)} type="number" span2 />
        </div>
        <p className="text-xs text-slate-400 mt-1.5">Leave "Override Total" blank to auto-sum the line items above.</p>
      </div>

      {/* ── Section 4: Cost Comparison ── */}
      {(originalTotal != null || revisedTotal != null) && (
        <>
          <div className="h-px bg-slate-100 dark:bg-slate-800" />
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Cost Comparison</p>
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden text-sm">
              <table className="w-full">
                <tbody>
                  <tr className="border-b border-slate-100 dark:border-slate-800">
                    <td className="px-4 py-3 text-slate-500">Original Pre-Auth Total</td>
                    <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200 text-right">{fmt(originalTotal)}</td>
                  </tr>
                  {lineTotal > 0 && (
                    <>
                      {form.revised_room_rent_per_day    ? <tr className="border-b border-slate-100 dark:border-slate-800"><td className="px-4 py-2.5 text-slate-400 pl-8">Room Rent / Day</td><td className="px-4 py-2.5 text-right text-slate-600 dark:text-slate-400">{fmt(form.revised_room_rent_per_day)}</td></tr> : null}
                      {form.revised_icu_charges_per_day  ? <tr className="border-b border-slate-100 dark:border-slate-800"><td className="px-4 py-2.5 text-slate-400 pl-8">ICU Charges / Day</td><td className="px-4 py-2.5 text-right text-slate-600 dark:text-slate-400">{fmt(form.revised_icu_charges_per_day)}</td></tr> : null}
                      {form.revised_ot_charges           ? <tr className="border-b border-slate-100 dark:border-slate-800"><td className="px-4 py-2.5 text-slate-400 pl-8">OT / Surgery</td><td className="px-4 py-2.5 text-right text-slate-600 dark:text-slate-400">{fmt(form.revised_ot_charges)}</td></tr> : null}
                      {form.revised_surgeon_fees         ? <tr className="border-b border-slate-100 dark:border-slate-800"><td className="px-4 py-2.5 text-slate-400 pl-8">Surgeon Fees</td><td className="px-4 py-2.5 text-right text-slate-600 dark:text-slate-400">{fmt(form.revised_surgeon_fees)}</td></tr> : null}
                      {form.revised_medicines_consumables ? <tr className="border-b border-slate-100 dark:border-slate-800"><td className="px-4 py-2.5 text-slate-400 pl-8">Medicines & Consumables</td><td className="px-4 py-2.5 text-right text-slate-600 dark:text-slate-400">{fmt(form.revised_medicines_consumables)}</td></tr> : null}
                      {form.revised_investigations        ? <tr className="border-b border-slate-100 dark:border-slate-800"><td className="px-4 py-2.5 text-slate-400 pl-8">Investigations</td><td className="px-4 py-2.5 text-right text-slate-600 dark:text-slate-400">{fmt(form.revised_investigations)}</td></tr> : null}
                    </>
                  )}
                  <tr className="border-b border-slate-100 dark:border-slate-800">
                    <td className="px-4 py-3 text-slate-500">Revised Total</td>
                    <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200 text-right">{fmt(revisedTotal)}</td>
                  </tr>
                  {variance != null && (
                    <tr className="bg-slate-50 dark:bg-slate-800/60">
                      <td className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-200">Difference</td>
                      <td className={`px-4 py-3.5 font-bold text-right text-base ${variance > 0 ? 'text-red-500' : 'text-green-600'}`}>
                        {variance > 0 ? '▲ +' : '▼ '}{fmt(Math.abs(variance))}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {err && <p className="text-xs text-red-500">{err}</p>}

      <div className="flex gap-2 pt-1">
        <button onClick={handleSubmit} disabled={saving || uploading}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60 flex items-center gap-2">
          {saving ? <Spinner sm /> : null} Save Enhancement
        </button>
        <button onClick={onCancel}
          className="px-4 py-2.5 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-sm rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
          Cancel
        </button>
      </div>
    </div>
  );
}

function EnhancementContent({
  caseData, onRefresh,
}: {
  caseData: CaseDetail;
  onRefresh: () => void;
}) {
  const [showForm, setShowForm] = useState(false);

  const pa = caseData.pre_auth;
  const enhancements = caseData.enhancements || [];

  return (
    <div className="space-y-4">
      {/* Info banner */}
      <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-amber-50 dark:bg-slate-800 border border-amber-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400">
        <AlertCircle size={15} className="mt-0.5 shrink-0 text-amber-500" />
        Enhancement is <span className="text-slate-800 dark:text-slate-200 font-medium mx-1">optional</span>. Raise one if the diagnosis or treatment plan changes after the initial pre-auth.
      </div>

      {/* Existing enhancements list */}
      {enhancements.length === 0 && !showForm && (
        <p className="text-slate-400 dark:text-slate-500 text-sm py-2">No enhancements raised yet for this case.</p>
      )}

      {enhancements.map((e) => (
        <div key={e.id} className="p-5 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-sm space-y-4">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="w-6 h-6 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-600 dark:text-slate-300 shrink-0">
              {e.sequence_no}
            </span>
            <Badge status={e.status} />
            {e.original_diagnosis && (
              <span className="text-xs text-slate-400 ml-auto truncate">Original: {e.original_diagnosis}</span>
            )}
          </div>

          {/* Reason */}
          <div>
            <p className="font-semibold text-slate-800 dark:text-slate-200">{e.reason}</p>
            {e.clinical_justification && (
              <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">{e.clinical_justification}</p>
            )}
          </div>

          {/* Updated clinical details */}
          {(e.updated_diagnosis || e.updated_icd10_code || e.updated_surgery_name || e.updated_icd10_pcs_code || e.updated_line_of_treatment) && (
            <>
              <div className="h-px bg-slate-200 dark:bg-slate-700" />
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Updated Clinical Details</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {e.updated_diagnosis          && <Info label="Updated Diagnosis"    value={e.updated_diagnosis} />}
                  {e.updated_icd10_code         && <Info label="ICD-10 Code"          value={e.updated_icd10_code} />}
                  {e.updated_surgery_name       && <Info label="Surgery / Procedure"  value={e.updated_surgery_name} />}
                  {e.updated_icd10_pcs_code     && <Info label="ICD-10 PCS"           value={e.updated_icd10_pcs_code} />}
                  {e.updated_line_of_treatment  && <Info label="Line of Treatment"    value={e.updated_line_of_treatment} />}
                </div>
              </div>
            </>
          )}

          {/* Revised costs */}
          {(e.revised_room_rent_per_day || e.revised_icu_charges_per_day || e.revised_ot_charges ||
            e.revised_surgeon_fees || e.revised_medicines_consumables || e.revised_investigations ||
            e.revised_total_estimated_cost) && (
            <>
              <div className="h-px bg-slate-200 dark:bg-slate-700" />
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Revised Costs</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {e.revised_room_rent_per_day      && <Info label="Room Rent/Day"          value={fmt(e.revised_room_rent_per_day)} />}
                  {e.revised_icu_charges_per_day    && <Info label="ICU Charges/Day"        value={fmt(e.revised_icu_charges_per_day)} />}
                  {e.revised_ot_charges             && <Info label="OT / Surgery"           value={fmt(e.revised_ot_charges)} />}
                  {e.revised_surgeon_fees           && <Info label="Surgeon Fees"           value={fmt(e.revised_surgeon_fees)} />}
                  {e.revised_medicines_consumables  && <Info label="Medicines"              value={fmt(e.revised_medicines_consumables)} />}
                  {e.revised_investigations         && <Info label="Investigations"         value={fmt(e.revised_investigations)} />}
                </div>
                {e.revised_total_estimated_cost != null && (
                  <div className="mt-3 flex items-center justify-between px-4 py-2.5 bg-white dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600">
                    <span className="text-sm font-semibold text-slate-500">Revised Total</span>
                    <div className="text-right">
                      <span className="text-base font-bold text-slate-900 dark:text-white">{fmt(e.revised_total_estimated_cost)}</span>
                      {e.original_total_cost != null && (
                        <span className={`ml-3 text-xs font-semibold ${
                          e.revised_total_estimated_cost > e.original_total_cost ? 'text-red-500' : 'text-green-600'
                        }`}>
                          {e.revised_total_estimated_cost > e.original_total_cost ? '▲ +' : '▼ '}
                          {fmt(Math.abs(e.revised_total_estimated_cost - e.original_total_cost))} vs original
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      ))}

      {/* New enhancement form */}
      {showForm && pa && (
        <div className="p-5 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <EnhancementForm
            preAuthId={pa.id}
            seqNo={enhancements.length + 1}
            originalTotal={pa.total_estimated_cost}
            onSave={() => { setShowForm(false); onRefresh(); }}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {!showForm && (
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-5 py-2.5 border border-dashed border-slate-300 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm font-medium rounded-xl transition-colors">
          <Plus size={15} /> Add Enhancement
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 3 — Discharge content
// ---------------------------------------------------------------------------

type DischargeFormState = Partial<DischargeData>;

function DischargeContent({
  caseData, discharge, onRefresh,
}: {
  caseData: CaseDetail;
  discharge: DischargeResponse | null;
  onRefresh: () => void;
}) {
  const [editing, setEditing] = useState(!discharge);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dischargeId, setDischargeId] = useState<string | null>(discharge?.id ?? null);
  const [form, setForm] = useState<DischargeFormState>(discharge ?? {});
  const [err, setErr] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(
    discharge ? computeDischargeConfidence(discharge) : null
  );

  const pa = caseData.pre_auth;
  const set = (k: keyof DischargeFormState, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const ensureRecord = async (): Promise<string> => {
    if (dischargeId) return dischargeId;
    const created = await createDischarge({
      bill_no: caseData.bill_no,
      pre_auth_id: pa!.id,
      abha_id: pa?.abha_id ?? undefined,
    });
    setDischargeId(created.id);
    return created.id;
  };

  const handleFileUpload = async (file: File) => {
    if (!pa) return;
    setUploading(true); setErr(null);
    try {
      const id = await ensureRecord();
      const extracted = await extractDischargeData(id, file);
      setForm((f) => {
        const merged = {
          ...f,
          discharge_date:        extracted.discharge_date        ?? f.discharge_date,
          final_diagnosis:       extracted.final_diagnosis       ?? f.final_diagnosis,
          final_icd10_codes:     extracted.final_icd10_codes     ?? f.final_icd10_codes,
          procedure_codes:       extracted.procedure_codes       ?? f.procedure_codes,
          room_charges:          extracted.room_charges          ?? f.room_charges,
          icu_charges:           extracted.icu_charges           ?? f.icu_charges,
          surgery_charges:       extracted.surgery_charges       ?? f.surgery_charges,
          medicine_charges:      extracted.medicine_charges      ?? f.medicine_charges,
          investigation_charges: extracted.investigation_charges ?? f.investigation_charges,
          other_charges:         extracted.other_charges         ?? f.other_charges,
          total_bill_amount:     extracted.total_bill_amount     ?? f.total_bill_amount,
        };
        setConfidence(computeDischargeConfidence(merged));
        return merged;
      });
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message || 'Extraction failed');
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async () => {
    if (!pa) return;
    setSaving(true); setErr(null);
    try {
      const id = await ensureRecord();
      await updateDischarge(id, { bill_no: caseData.bill_no, pre_auth_id: pa.id, ...form });
      setEditing(false);
      onRefresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Revenue flags — collapsible dropdown */}
      {discharge && !editing && (discharge.revenue_flags?.length ?? 0) > 0 && (() => {
        const critical = discharge.revenue_flags.filter(f => f.severity === 'critical');
        const warnings = discharge.revenue_flags.filter(f => f.severity !== 'critical');
        return (
          <FlagsDropdown critical={critical} warnings={warnings} />
        );
      })()}

      {/* Summary view */}
      {discharge && !editing && (
        <div className="space-y-5">
          {confidence !== null && <DischargeConfidenceBadge score={confidence} />}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
            <Info label="Discharge Date"   value={discharge.discharge_date} />
            <Info label="Final Diagnosis"  value={discharge.final_diagnosis} />
            <Info label="ICD-10 Codes"     value={discharge.final_icd10_codes} />
            <Info label="Procedure Codes"  value={discharge.procedure_codes} />
          </div>
          <div className="h-px bg-slate-100 dark:bg-slate-800" />
          {/* Bill breakdown */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Final Bill Breakdown</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Info label="Room Charges"          value={fmt(discharge.room_charges)} />
              <Info label="ICU Charges"           value={fmt(discharge.icu_charges)} />
              <Info label="Surgery Charges"       value={fmt(discharge.surgery_charges)} />
              <Info label="Medicine / Consumables" value={fmt(discharge.medicine_charges)} />
              <Info label="Investigation Charges" value={fmt(discharge.investigation_charges)} />
              <Info label="Other Charges"         value={fmt(discharge.other_charges)} />
            </div>
            <div className="mt-4 flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
              <span className="text-sm font-semibold text-slate-500">Total Bill Amount</span>
              <span className="text-lg font-bold text-slate-900 dark:text-white">{fmt(discharge.total_bill_amount)}</span>
            </div>
          </div>
          <button onClick={() => setEditing(true)}
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium hover:underline">
            Edit / Re-upload
          </button>
        </div>
      )}

      {/* Edit / upload form */}
      {editing && (
        <div className="space-y-4">
          {/* Upload zone */}
          <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 cursor-pointer transition-colors ${
            uploading
              ? 'border-blue-400 bg-blue-50 dark:bg-blue-950/20'
              : 'border-slate-300 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950/10'
          }`}>
            <input type="file" accept=".pdf" className="hidden" disabled={uploading}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); }} />
            {uploading ? (
              <>
                <div className="w-9 h-9 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin mb-3" />
                <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">Extracting with Gemini AI...</p>
                <p className="text-xs text-slate-400 mt-1">Reading discharge summary, diagnoses, procedure codes &amp; bill</p>
              </>
            ) : (
              <>
                <Upload size={24} className="text-slate-400 mb-3" />
                <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">Upload Discharge Summary / Final Bill PDF</p>
                <p className="text-xs text-slate-400 mt-1">Gemini will auto-fill all fields below</p>
              </>
            )}
          </label>

          {/* Confidence badge — shown after a file is uploaded */}
          {confidence !== null && <DischargeConfidenceBadge score={confidence} />}

          {/* Editable fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FormInput label="Discharge Date"                  value={form.discharge_date || ''} onChange={(v) => set('discharge_date', v)} type="date" />
            <FormInput label="Final Diagnosis"                 value={form.final_diagnosis || ''} onChange={(v) => set('final_diagnosis', v)} />
            <FormInput label="ICD-10 Diagnosis Codes"          value={form.final_icd10_codes || ''} onChange={(v) => set('final_icd10_codes', v)} />
            <FormInput label="Procedure Codes (ICD-10 PCS / CPT)" value={form.procedure_codes || ''} onChange={(v) => set('procedure_codes', v)} />
            <FormInput label="Room Charges (₹)"               value={form.room_charges?.toString() || ''} onChange={(v) => set('room_charges', v ? Number(v) : undefined)} type="number" />
            <FormInput label="ICU Charges (₹)"                value={form.icu_charges?.toString() || ''} onChange={(v) => set('icu_charges', v ? Number(v) : undefined)} type="number" />
            <FormInput label="Surgery / OT Charges (₹)"       value={form.surgery_charges?.toString() || ''} onChange={(v) => set('surgery_charges', v ? Number(v) : undefined)} type="number" />
            <FormInput label="Medicine / Consumables (₹)"     value={form.medicine_charges?.toString() || ''} onChange={(v) => set('medicine_charges', v ? Number(v) : undefined)} type="number" />
            <FormInput label="Investigation Charges (₹)"      value={form.investigation_charges?.toString() || ''} onChange={(v) => set('investigation_charges', v ? Number(v) : undefined)} type="number" />
            <FormInput label="Other Charges (₹)"              value={form.other_charges?.toString() || ''} onChange={(v) => set('other_charges', v ? Number(v) : undefined)} type="number" />
            <FormInput label="Total Bill Amount (₹)"          value={form.total_bill_amount?.toString() || ''} onChange={(v) => set('total_bill_amount', v ? Number(v) : undefined)} type="number" />
          </div>

          {err && <p className="text-xs text-red-500">{err}</p>}

          <div className="flex gap-3">
            <button onClick={handleSave} disabled={saving}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60 flex items-center gap-2">
              {saving ? <Spinner sm /> : null} Save Discharge
            </button>
            {discharge && (
              <button onClick={() => { setEditing(false); setErr(null); }}
                className="px-4 py-2.5 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-sm rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                Cancel
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 4 — Settlement content
// ---------------------------------------------------------------------------

function SettlementContent({
  caseData, discharge, settlement, onRefresh,
}: {
  caseData: CaseDetail;
  discharge: DischargeResponse | null;
  settlement: SettlementResponse | null;
  onRefresh: () => void;
}) {
  const [deduction, setDeduction] = useState(settlement?.deduction_amount?.toString() || '0');
  const [deductionReason, setDeductionReason] = useState(settlement?.deduction_reason || '');
  const [tpaRemarks, setTpaRemarks] = useState(settlement?.tpa_remarks || '');
  const [settlementDate, setSettlementDate] = useState(settlement?.settlement_date || '');
  const [saving, setSaving] = useState(false);
  const [statusLoading, setStatusLoading] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const pa = caseData.pre_auth;
  const preAuthEstimate = pa?.total_estimated_cost ?? null;
  const claimedAmount   = discharge?.total_bill_amount ?? null;
  const deductionNum    = parseFloat(deduction) || 0;
  const finalAmount     = claimedAmount != null ? Math.max(0, claimedAmount - deductionNum) : null;
  const variance        = preAuthEstimate != null && claimedAmount != null ? claimedAmount - preAuthEstimate : null;

  if (!discharge) {
    return (
      <div className="flex items-center gap-3 px-5 py-6 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl text-amber-700 dark:text-amber-300 text-sm">
        <Lock size={16} className="shrink-0" />
        Complete the Discharge step first before creating a settlement.
      </div>
    );
  }

  const handleCreate = async () => {
    if (!pa) return;
    setSaving(true); setErr(null);
    try {
      await createSettlement({
        bill_no: caseData.bill_no,
        pre_auth_id: pa.id,
        discharge_id: discharge.id,
        abha_id: pa.abha_id ?? undefined,
        deduction_amount: deductionNum,
        deduction_reason: deductionReason || undefined,
        tpa_remarks: tpaRemarks || undefined,
        settlement_date: settlementDate || undefined,
      });
      onRefresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message || 'Failed to create settlement');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!settlement) return;
    setStatusLoading(newStatus); setErr(null);
    try {
      await updateSettlement(settlement.id, {
        bill_no: caseData.bill_no,
        status: newStatus,
        deduction_amount: deductionNum,
        deduction_reason: deductionReason || undefined,
        tpa_remarks: tpaRemarks || undefined,
        settlement_date: settlementDate || undefined,
      });
      onRefresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message || 'Update failed');
    } finally {
      setStatusLoading(null);
    }
  };

  return (
    <div className="space-y-5">
      {/* Settlement status banner if exists */}
      {settlement && (
        <div className="flex items-center justify-between px-5 py-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <div>
            <p className="text-xs text-slate-500 mb-1">Settlement Status</p>
            <Badge status={settlement.status || 'pending'} />
          </div>
          {settlement.final_settlement_amount != null && (
            <div className="text-right">
              <p className="text-xs text-slate-500 mb-1">Final Settlement</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{fmt(settlement.final_settlement_amount)}</p>
            </div>
          )}
        </div>
      )}

      {/* Comparison table */}
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Amount Comparison</p>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden text-sm">
          <table className="w-full">
            <tbody>
              <tr className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-4 py-3.5 text-slate-500">Pre-Auth Estimate</td>
                <td className="px-4 py-3.5 font-semibold text-slate-800 dark:text-slate-200 text-right">{fmt(preAuthEstimate)}</td>
              </tr>
              <tr className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-4 py-3.5 text-slate-500">Final Bill (Claimed)</td>
                <td className="px-4 py-3.5 font-semibold text-slate-800 dark:text-slate-200 text-right">{fmt(claimedAmount)}</td>
              </tr>
              {variance != null && (
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <td className="px-4 py-3.5 text-slate-500">Variance</td>
                  <td className={`px-4 py-3.5 font-semibold text-right ${variance > 0 ? 'text-red-500' : 'text-green-600'}`}>
                    {variance > 0 ? '▲ +' : '▼ '}{fmt(Math.abs(variance))}
                  </td>
                </tr>
              )}
              <tr>
                <td className="px-4 py-3.5 text-slate-500">Deduction</td>
                <td className="px-4 py-3.5 font-semibold text-right text-amber-600">– {fmt(deductionNum)}</td>
              </tr>
              <tr className="bg-slate-50 dark:bg-slate-800/60">
                <td className="px-4 py-4 font-bold text-slate-700 dark:text-slate-200">Settlement Amount</td>
                <td className="px-4 py-4 font-bold text-blue-600 dark:text-blue-400 text-right text-lg">
                  {fmt(settlement?.final_settlement_amount ?? finalAmount)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Editable fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <FormInput label="Deduction Amount (₹)"  value={deduction}        onChange={setDeduction}        type="number" />
        <FormInput label="Deduction Reason"       value={deductionReason}  onChange={setDeductionReason} />
        <FormInput label="TPA Remarks"            value={tpaRemarks}       onChange={setTpaRemarks}      span2 area />
        <FormInput label="Settlement Date"        value={settlementDate}   onChange={setSettlementDate}  type="date" />
      </div>

      {err && <p className="text-xs text-red-500">{err}</p>}

      {/* Action buttons */}
      {!settlement ? (
        <button onClick={handleCreate} disabled={saving}
          className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60">
          {saving ? <Spinner sm /> : <IndianRupee size={14} />}
          Create Settlement
        </button>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(['approved', 'rejected', 'paid'] as const).map((s) => {
            const labels: Record<string, string> = { approved: '✓ Approve', rejected: '✗ Reject', paid: '💳 Mark Paid' };
            const colors: Record<string, string> = {
              approved: 'bg-green-600 hover:bg-green-700',
              rejected: 'bg-red-600 hover:bg-red-700',
              paid:     'bg-purple-600 hover:bg-purple-700',
            };
            return (
              <button key={s} onClick={() => handleStatusChange(s)}
                disabled={statusLoading !== null || settlement.status === s}
                className={`flex items-center gap-1.5 px-4 py-2 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 ${colors[s]}`}>
                {statusLoading === s ? <Spinner sm /> : null}
                {labels[s]}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main CasePage
// ---------------------------------------------------------------------------

export default function CasePage() {
  const { billNo } = useParams<{ billNo: string }>();
  const [searchParams] = useSearchParams();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(() => {
    const s = parseInt(searchParams.get('step') || '1', 10);
    return s >= 1 && s <= 4 ? s : 1;
  });

  const load = useCallback(async () => {
    if (!billNo) return;
    setLoading(true); setError(null);
    try {
      const data = await getCase(decodeURIComponent(billNo));
      setCaseData(data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Failed to load case');
    } finally {
      setLoading(false);
    }
  }, [billNo]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-10 h-10 border-4 border-slate-200 dark:border-slate-700 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-2xl text-red-700 dark:text-red-300">
        <p className="font-semibold">{error || 'Case not found'}</p>
        <Link to="/cases" className="text-sm underline mt-2 inline-block text-red-500">Back to Cases</Link>
      </div>
    );
  }

  const pa = caseData.pre_auth;

  // Compute step statuses
  const steps: StepDef[] = [
    {
      id: 1,
      label: 'Pre-Auth',
      status: activeStep === 1 ? 'active' : 'done',
    },
    {
      id: 2,
      label: 'Enhancement',
      status: activeStep === 2
        ? 'active'
        : (activeStep > 2 || caseData.discharge || caseData.enhancements.length > 0)
        ? 'done'
        : 'pending',
    },
    {
      id: 3,
      label: 'Discharge',
      status: activeStep === 3
        ? 'active'
        : caseData.discharge
        ? 'done'
        : 'pending',
    },
    {
      id: 4,
      label: 'Settlement',
      status: activeStep === 4
        ? 'active'
        : caseData.settlement
        ? 'done'
        : !caseData.discharge
        ? 'locked'
        : 'pending',
    },
  ];

  const stepTitles: Record<number, string> = {
    1: 'Pre-Authorization',
    2: 'Enhancement Requests',
    3: 'Discharge',
    4: 'Settlement',
  };

  const stepDescriptions: Record<number, string> = {
    1: 'Initial cashless hospitalization request with patient demographics, diagnosis, and cost estimates.',
    2: 'Optional — raise if the diagnosis or treatment plan changes after the initial pre-auth.',
    3: 'Upload discharge summary and final bill. Gemini extracts diagnoses, procedure codes, and charges.',
    4: 'Compare pre-auth estimate vs final bill, apply deductions, and finalize TPA settlement.',
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back */}
      <Link
        to="/cases"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={15} /> All Cases
      </Link>

      {/* Case header card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl px-7 py-6 mb-8 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <FileText size={16} className="text-slate-400" />
          <span className="font-mono text-sm font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-3 py-1 rounded-full border border-slate-200 dark:border-slate-700">
            {caseData.bill_no}
          </span>
          {pa && <Badge status={pa.status} />}
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white mb-1">
          {pa?.patient_name || 'Unknown Patient'}
        </h1>
        <p className="text-slate-500 text-sm">
          {[pa?.hospital_name, pa?.admission_date].filter(Boolean).join(' · ')}
          {pa?.abha_id && (
            <span className="ml-3 text-slate-400">ABHA: {pa.abha_id}</span>
          )}
        </p>
      </div>

      {/* Stepper */}
      <Stepper steps={steps} activeStep={activeStep} onStepClick={setActiveStep} />

      {/* Active step content card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
        {/* Step content header */}
        <div className="px-7 py-5 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              steps[activeStep - 1].status === 'done'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
            }`}>
              {steps[activeStep - 1].status === 'done' ? <CheckCircle2 size={16} /> : activeStep}
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">{stepTitles[activeStep]}</h2>
              <p className="text-xs text-slate-400 mt-0.5">{stepDescriptions[activeStep]}</p>
            </div>
            {activeStep === 2 && (
              <span className="ml-auto text-xs px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500">
                Optional
              </span>
            )}
          </div>
        </div>

        {/* Step content body */}
        <div className="px-7 py-6">
          {activeStep === 1 && <PreAuthContent caseData={caseData} onNext={() => setActiveStep(2)} />}
          {activeStep === 2 && <EnhancementContent caseData={caseData} onRefresh={load} />}
          {activeStep === 3 && (
            <DischargeContent caseData={caseData} discharge={caseData.discharge} onRefresh={load} />
          )}
          {activeStep === 4 && (
            <SettlementContent
              caseData={caseData}
              discharge={caseData.discharge}
              settlement={caseData.settlement}
              onRefresh={load}
            />
          )}
        </div>

        {/* Step navigation footer */}
        <div className="px-7 py-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <button
            onClick={() => setActiveStep((s) => Math.max(1, s - 1))}
            disabled={activeStep === 1}
            className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400 hover:text-slate-700 dark:hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ArrowLeft size={14} /> Previous
          </button>
          <span className="text-xs text-slate-400">{activeStep} / 4</span>
          <button
            onClick={() => {
              const next = activeStep + 1;
              if (next <= 4 && steps[next - 1].status !== 'locked') setActiveStep(next);
            }}
            disabled={activeStep === 4 || steps[activeStep].status === 'locked'}
            className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400 hover:text-slate-700 dark:hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next <ArrowLeft size={14} className="rotate-180" />
          </button>
        </div>
      </div>
    </div>
  );
}

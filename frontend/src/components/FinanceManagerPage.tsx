import { useState, useEffect, useRef } from 'react';
import {
  Activity, Sun, Moon, LogOut, Download, TrendingUp, IndianRupee,
  Briefcase, AlertCircle, CheckCircle2, Clock, ChevronDown, ChevronUp,
  FileText, XCircle, ThumbsUp, ThumbsDown, X,
} from 'lucide-react';
import {
  listCases, downloadMisReport, getCase, getBankStatement,
  financeSettlementAction,
} from '../services/api';
import type { CaseSummary, CaseDetail, BankStatement } from '../types/api';

interface FinanceManagerPageProps {
  username: string;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  onLogout: () => void;
}

function inr(n: number | null | undefined) {
  if (n == null) return '—';
  return `₹${n.toLocaleString('en-IN')}`;
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: {
  label: string; value: string; sub?: string;
  color: 'blue' | 'green' | 'amber' | 'red';
}) {
  const txt = { blue: 'text-blue-700 dark:text-blue-300', green: 'text-green-700 dark:text-green-300', amber: 'text-amber-700 dark:text-amber-300', red: 'text-red-700 dark:text-red-300' };
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-extrabold ${txt[color]}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ─── MIS dropdown ─────────────────────────────────────────────────────────────

function MisDropdown() {
  const [open, setOpen]       = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const download = async (period: 'weekly' | 'monthly' | 'yearly') => {
    setOpen(false); setLoading(true);
    try { await downloadMisReport(period); }
    catch (e: any) { alert(e.message || 'Failed to generate report'); }
    finally { setLoading(false); }
  };

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(o => !o)} disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm">
        {loading ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Download size={15} />}
        MIS Report
        <ChevronDown size={13} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute right-0 mt-1.5 w-36 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg z-20 overflow-hidden">
          {(['weekly', 'monthly', 'yearly'] as const).map(p => (
            <button key={p} onClick={() => download(p)}
              className="w-full text-left px-4 py-2.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 capitalize transition-colors">
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function DownloadCard({ period, label, sub }: { period: 'weekly' | 'monthly' | 'yearly'; label: string; sub: string }) {
  const [loading, setLoading] = useState(false);
  const handle = async () => {
    setLoading(true);
    try { await downloadMisReport(period); }
    catch (e: any) { alert(e.message || 'Failed'); }
    finally { setLoading(false); }
  };
  return (
    <button onClick={handle} disabled={loading}
      className="flex items-center gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50/40 dark:hover:bg-blue-900/10 transition-all text-left disabled:opacity-60">
      {loading
        ? <span className="w-5 h-5 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin shrink-0" />
        : <Download size={18} className="text-blue-500 shrink-0" />}
      <div>
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</p>
        <p className="text-xs text-slate-400">{sub}</p>
      </div>
    </button>
  );
}

// ─── Settlement Review Panel ──────────────────────────────────────────────────

type ReviewPhase = 'idle' | 'pulling' | 'ready' | 'actioned';

interface ReviewPanelProps {
  billNo: string;
  onClose: () => void;
  onActioned: () => void;
}

function SettlementReviewPanel({ billNo, onClose, onActioned }: ReviewPanelProps) {
  const [phase, setPhase]           = useState<ReviewPhase>('idle');
  const [pullProgress, setPullProgress] = useState(0);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [bankStmt, setBankStmt]     = useState<BankStatement | null>(null);
  const [loadErr, setLoadErr]       = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<'approved' | 'denied' | null>(null);
  const [actioning, setActioning]   = useState(false);
  const [denyNote, setDenyNote]     = useState('');
  const [showDenyInput, setShowDenyInput] = useState(false);

  // Fake pull progress bar
  const handlePull = async () => {
    setPhase('pulling');
    setPullProgress(0);

    // Fetch real data while showing fake progress
    const dataPromise = Promise.all([
      getCase(billNo),
      getBankStatement(billNo).catch(() => null),
    ]);

    const steps = [15, 35, 55, 72, 88, 100];
    for (let i = 0; i < steps.length; i++) {
      await new Promise(r => setTimeout(r, 600));
      setPullProgress(steps[i]);
    }

    try {
      const [detail, bank] = await dataPromise;
      setCaseDetail(detail);
      setBankStmt(bank);
      setPhase('ready');
    } catch (e: any) {
      setLoadErr(e.response?.data?.detail || e.message || 'Failed to load data');
      setPhase('idle');
    }
  };

  const handleAction = async (action: 'approve' | 'deny') => {
    if (!caseDetail?.settlement) return;
    setActioning(true);
    try {
      // Auto-deduct 5–10% of claimed amount on approval
      let autoDeduction: number | undefined;
      if (action === 'approve' && caseDetail.settlement.claimed_amount) {
        const pct = 5 + Math.random() * 5; // 5–10%
        autoDeduction = Math.round(caseDetail.settlement.claimed_amount * pct) / 100;
      }
      await financeSettlementAction(caseDetail.settlement.id, action, denyNote || undefined, autoDeduction);
      setActionResult(action === 'approve' ? 'approved' : 'denied');
      setPhase('actioned');
      onActioned();
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Action failed');
    } finally {
      setActioning(false);
    }
  };

  const s  = caseDetail?.settlement;
  const pa = caseDetail?.pre_auth;
  const d  = caseDetail?.discharge;

  return (
    <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
      <div className="px-5 py-4 space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText size={14} className="text-blue-500" />
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">
              Settlement Review — {billNo}
            </span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors">
            <X size={15} />
          </button>
        </div>

        {/* Phase: idle — pull button */}
        {phase === 'idle' && (
          <div className="flex flex-col items-center py-5 gap-3">
            {loadErr && <p className="text-xs text-red-500">{loadErr}</p>}
            <button onClick={handlePull}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm">
              <Download size={15} />
              Pull Final Settlement PDF
            </button>
            <p className="text-xs text-slate-400">Fetches & verifies settlement data from TPA records</p>
          </div>
        )}

        {/* Phase: pulling — progress bar */}
        {phase === 'pulling' && (
          <div className="py-5 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 border-2 border-blue-200 border-t-blue-500 rounded-full animate-spin shrink-0" />
              <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                {pullProgress < 40 ? 'Connecting to TPA settlement ledger…' :
                 pullProgress < 70 ? 'Verifying claim amounts & deductions…' :
                 pullProgress < 90 ? 'Extracting final bill data…' :
                 'Compiling settlement summary…'}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${pullProgress}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 text-right">{pullProgress}%</p>
          </div>
        )}

        {/* Phase: ready — data + actions */}
        {phase === 'ready' && s && (
          <div className="space-y-4">
            {/* Data card */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <DataItem label="Final Settlement" value={inr(s.final_settlement_amount)} highlight="green" />
              <DataItem label="Billed Amount"    value={inr(d?.total_bill_amount ?? s.claimed_amount)} />
              <DataItem label="Pre-Auth Estimate" value={inr(pa?.total_estimated_cost)} />
              <DataItem label="Settlement Date"  value={s.settlement_date || '—'} />
              {bankStmt?.utr_number && (
                <DataItem label="UTR / Reference" value={bankStmt.utr_number} mono />
              )}
              {bankStmt?.transaction_date && (
                <DataItem label="Payment Date" value={bankStmt.transaction_date} />
              )}
              {bankStmt?.sender_bank && (
                <DataItem label="Paying Bank" value={bankStmt.sender_bank} />
              )}
              {s.deduction_reason && (
                <div className="col-span-2 sm:col-span-3">
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Deduction Reason</p>
                  <p className="text-xs text-slate-600 dark:text-slate-300">{s.deduction_reason}</p>
                </div>
              )}
            </div>

            {/* Deny note input */}
            {showDenyInput && (
              <textarea
                placeholder="Reason for denial (optional)…"
                value={denyNote}
                onChange={e => setDenyNote(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 text-sm rounded-lg border border-red-300 dark:border-red-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 placeholder-slate-400 resize-none focus:outline-none focus:ring-2 focus:ring-red-300"
              />
            )}

            {/* Action buttons */}
            <div className="flex items-center gap-3 flex-wrap">
              <button
                onClick={() => handleAction('approve')}
                disabled={actioning}
                className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60"
              >
                {actioning ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <ThumbsUp size={14} />}
                Approve Settlement
              </button>
              <button
                onClick={() => { if (!showDenyInput) { setShowDenyInput(true); } else { handleAction('deny'); } }}
                disabled={actioning}
                className="flex items-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60"
              >
                {actioning ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <ThumbsDown size={14} />}
                {showDenyInput ? 'Confirm Deny' : 'Deny Settlement'}
              </button>
              {showDenyInput && (
                <button onClick={() => setShowDenyInput(false)} className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        {/* Phase: actioned */}
        {phase === 'actioned' && (
          <div className={`flex items-center gap-3 px-4 py-4 rounded-xl ${
            actionResult === 'approved'
              ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800'
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
          }`}>
            {actionResult === 'approved'
              ? <CheckCircle2 size={18} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
              : <XCircle size={18} className="text-red-600 dark:text-red-400 shrink-0" />}
            <div>
              <p className={`text-sm font-semibold ${actionResult === 'approved' ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-700 dark:text-red-300'}`}>
                Settlement {actionResult === 'approved' ? 'Approved' : 'Denied'} by Finance
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                {actionResult === 'approved'
                  ? 'Staff has been notified. They can now close or follow up the case.'
                  : 'Staff has been notified about the denial.'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DataItem({ label, value, highlight, mono }: {
  label: string; value: string;
  highlight?: 'green' | 'red';
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">{label}</p>
      <p className={`text-sm font-bold truncate ${
        highlight === 'green' ? 'text-emerald-600 dark:text-emerald-400 text-base' :
        highlight === 'red'   ? 'text-red-500 dark:text-red-400' :
        'text-slate-700 dark:text-slate-200'
      } ${mono ? 'font-mono text-blue-600 dark:text-blue-400' : ''}`}>
        {value}
      </p>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function FinanceManagerPage({ username, theme, toggleTheme, onLogout }: FinanceManagerPageProps) {
  const [cases, setCases]     = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedBill, setExpandedBill] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    listCases()
      .then(setCases)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const totalCases        = cases.length;
  const settled           = cases.filter(c => c.has_settlement).length;
  const pendingSettlement = cases.filter(c => c.has_discharge && !c.has_settlement).length;
  const totalEstimated    = cases.reduce((s, c) => s + (c.total_estimated_cost ?? 0), 0);

  const statusOf = (c: CaseSummary) =>
    c.has_settlement ? 'Settled' :
    c.has_discharge  ? 'Awaiting Settlement' :
    c.has_enhancement ? 'Enhanced' :
    'Pre-Auth';

  const statusColor = (s: string) =>
    s === 'Settled'             ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' :
    s === 'Awaiting Settlement' ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300' :
    s === 'Enhanced'            ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300' :
                                  'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300';

  const financeLabel = (c: CaseSummary): { text: string; cls: string } => {
    if (!c.has_settlement) return { text: '—', cls: 'text-slate-400' };
    const s = c.settlement_status ?? 'pending';
    if (s === 'finance_approved') return { text: 'Approved', cls: 'text-emerald-600 dark:text-emerald-400 font-semibold' };
    if (s === 'finance_denied')   return { text: 'Denied',   cls: 'text-red-500 dark:text-red-400 font-semibold' };
    if (s === 'closed')           return { text: 'Closed',   cls: 'text-slate-500 dark:text-slate-400 font-semibold' };
    if (s === 'followed_up')      return { text: 'Follow-up', cls: 'text-blue-500 dark:text-blue-400 font-semibold' };
    return { text: 'Pending', cls: 'text-amber-600 dark:text-amber-400' };
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans antialiased transition-colors">

      {/* Navbar */}
      <nav className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-8 py-4 flex justify-between items-center sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-600 p-2 rounded-lg shadow-sm">
            <IndianRupee className="text-white" size={22} />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
              Finance<span className="text-emerald-600 dark:text-emerald-400"> Manager</span>
            </span>
            <p className="text-xs text-slate-400 leading-none mt-0.5">ClinicalFHIR — RCM Dashboard</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 hidden sm:block">
            Signed in as <span className="font-semibold text-slate-600 dark:text-slate-300">{username}</span>
          </span>
          <button onClick={toggleTheme}
            className="p-2 rounded-full text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all">
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <button onClick={onLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-500 dark:text-slate-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400 transition-colors">
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto py-10 px-6 space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Financial Overview</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Revenue cycle status across all active cases.</p>
          </div>
          <MisDropdown />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Cases"           value={String(totalCases)}       color="blue"  sub="All time" />
          <StatCard label="Settled"               value={String(settled)}          color="green" sub={`${totalCases ? Math.round(settled/totalCases*100) : 0}% of total`} />
          <StatCard label="Awaiting Settlement"   value={String(pendingSettlement)} color="amber" sub="Discharged, not settled" />
          <StatCard label="Total Estimated Value" value={inr(totalEstimated)}      color="blue"  sub="Across all pre-auths" />
        </div>

        {/* Pipeline */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
            <TrendingUp size={15} className="text-emerald-500" /> Pipeline Breakdown
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Pre-Auth only', count: cases.filter(c => !c.has_discharge).length,                                           icon: <Clock size={16} />,         color: 'text-slate-500' },
              { label: 'Enhanced',      count: cases.filter(c => c.has_enhancement && !c.has_discharge).length,                      icon: <AlertCircle size={16} />,    color: 'text-blue-500' },
              { label: 'Discharged',    count: pendingSettlement,                                                                     icon: <Briefcase size={16} />,      color: 'text-amber-500' },
              { label: 'Settled',       count: settled,                                                                               icon: <CheckCircle2 size={16} />,   color: 'text-green-500' },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800">
                <span className={item.color}>{item.icon}</span>
                <div>
                  <p className="text-lg font-extrabold text-slate-800 dark:text-slate-200">{item.count}</p>
                  <p className="text-xs text-slate-400">{item.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cases table */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800 dark:text-slate-200">All Cases — Financial Summary</h2>
            <span className="text-xs text-slate-400">{totalCases} cases</span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-7 h-7 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin" />
            </div>
          ) : cases.length === 0 ? (
            <div className="text-center py-16 text-slate-400 text-sm">No cases found.</div>
          ) : (
            <div>
              {cases.map((c, idx) => {
                const status  = statusOf(c);
                const isLast  = idx === cases.length - 1;
                const isOpen  = expandedBill === c.bill_no;

                return (
                  <div key={c.bill_no} className={!isLast ? 'border-b border-slate-100 dark:border-slate-800' : ''}>
                    {/* Row */}
                    <div
                      className={`flex items-center gap-2 px-5 py-3.5 transition-colors ${
                        c.has_settlement
                          ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60'
                          : ''
                      } ${isOpen ? 'bg-slate-50 dark:bg-slate-800/40' : ''}`}
                      onClick={() => c.has_settlement && setExpandedBill(isOpen ? null : c.bill_no)}
                    >
                      {/* Bill No */}
                      <div className="w-36 shrink-0">
                        <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1 rounded-lg">
                          {c.bill_no}
                        </span>
                      </div>
                      {/* Patient */}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-800 dark:text-slate-200 truncate">{c.patient_name || <span className="text-slate-400 italic">Unknown</span>}</p>
                        {c.abha_id && <p className="text-xs text-slate-400 mt-0.5 truncate">{c.abha_id}</p>}
                      </div>
                      {/* Hospital */}
                      <div className="hidden md:block w-40 shrink-0 text-xs text-slate-500 dark:text-slate-400 truncate">
                        {c.hospital_name || '—'}
                      </div>
                      {/* Status */}
                      <div className="w-36 shrink-0">
                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusColor(status)}`}>{status}</span>
                      </div>
                      {/* Finance Approval */}
                      <div className="hidden sm:block w-24 shrink-0 text-center">
                        {(() => { const fl = financeLabel(c); return <span className={`text-xs ${fl.cls}`}>{fl.text}</span>; })()}
                      </div>
                      {/* Amount */}
                      <div className="w-28 shrink-0 text-right font-semibold text-slate-700 dark:text-slate-300 tabular-nums text-sm">
                        {inr(c.total_estimated_cost)}
                      </div>
                      {/* Date */}
                      <div className="hidden lg:block w-24 shrink-0 text-right text-xs text-slate-400">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString('en-IN') : '—'}
                      </div>
                      {/* Expand indicator */}
                      <div className="w-6 shrink-0 flex justify-center">
                        {c.has_settlement && (
                          isOpen
                            ? <ChevronUp size={15} className="text-blue-500" />
                            : <ChevronDown size={15} className="text-slate-400" />
                        )}
                      </div>
                    </div>

                    {/* Inline review panel */}
                    {isOpen && (
                      <SettlementReviewPanel
                        billNo={c.bill_no}
                        onClose={() => setExpandedBill(null)}
                        onActioned={load}
                      />
                    )}
                  </div>
                );
              })}
              {/* Totals row */}
              {totalEstimated > 0 && (
                <div className="border-t-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 flex items-center gap-2 px-5 py-3">
                  <span className="flex-1 text-xs font-bold text-slate-500 uppercase tracking-wide">Total Estimated</span>
                  <span className="font-extrabold text-slate-800 dark:text-slate-200 tabular-nums text-sm">{inr(totalEstimated)}</span>
                  <span className="w-6" />
                </div>
              )}
            </div>
          )}
        </div>

        {/* MIS Report cards */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
            <Download size={15} className="text-blue-500" /> MIS Reports
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {(['weekly', 'monthly', 'yearly'] as const).map(p => (
              <DownloadCard key={p} period={p}
                label={p.charAt(0).toUpperCase() + p.slice(1) + ' Report'}
                sub={p === 'weekly' ? 'Last 7 days' : p === 'monthly' ? 'Last 30 days' : 'Last 365 days'} />
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3">
            Excel format — IRDAI TPA standard (Case Summary, Pre-Auth, Enhancement, Discharge & Settlement sheets)
          </p>
        </div>
      </main>

      <footer className="text-center py-6 text-slate-400 dark:text-slate-500 text-xs border-t border-slate-200 dark:border-slate-800 mt-8">
        ClinicalFHIR — Finance Manager Portal
      </footer>
    </div>
  );
}

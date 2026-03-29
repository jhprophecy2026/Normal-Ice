import { useState, useEffect } from 'react';
import {
  Activity, Sun, Moon, LogOut, Download, TrendingUp, IndianRupee,
  Briefcase, AlertCircle, CheckCircle2, Clock, ChevronDown,
} from 'lucide-react';
import { listCases, downloadMisReport } from '../services/api';
import type { CaseSummary } from '../types/api';

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

function StatCard({
  label, value, sub, color,
}: { label: string; value: string; sub?: string; color: 'blue' | 'green' | 'amber' | 'red' }) {
  const bg  = { blue: 'bg-blue-50 dark:bg-blue-900/20',   green: 'bg-green-50 dark:bg-green-900/20',   amber: 'bg-amber-50 dark:bg-amber-900/20',   red: 'bg-red-50 dark:bg-red-900/20'   };
  const txt = { blue: 'text-blue-700 dark:text-blue-300', green: 'text-green-700 dark:text-green-300', amber: 'text-amber-700 dark:text-amber-300', red: 'text-red-700 dark:text-red-300' };
  return (
    <div className={`rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5`}>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-extrabold ${txt[color]}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function MisDropdown() {
  const [open, setOpen]       = useState(false);
  const [loading, setLoading] = useState(false);

  const download = async (period: 'weekly' | 'monthly' | 'yearly') => {
    setOpen(false); setLoading(true);
    try { await downloadMisReport(period); }
    catch (e: any) { alert(e.message || 'Failed to generate report'); }
    finally { setLoading(false); }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm"
      >
        {loading
          ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          : <Download size={15} />}
        Download MIS Report
        <ChevronDown size={13} className={`transition-transform duration-150 ${open ? 'rotate-180' : ''}`} />
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

export default function FinanceManagerPage({ username, theme, toggleTheme, onLogout }: FinanceManagerPageProps) {
  const [cases, setCases]   = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listCases()
      .then(setCases)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Derived stats
  const totalCases     = cases.length;
  const settled        = cases.filter(c => c.has_settlement).length;
  const pendingSettlement = cases.filter(c => c.has_discharge && !c.has_settlement).length;
  const preAuthOnly    = cases.filter(c => !c.has_discharge).length;
  const totalEstimated = cases.reduce((s, c) => s + (c.total_estimated_cost ?? 0), 0);

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
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto py-10 px-6 space-y-8">

        {/* Page header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Financial Overview</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Revenue cycle status across all active cases.
            </p>
          </div>
          <MisDropdown />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Cases"           value={String(totalCases)}          color="blue"  sub="All time" />
          <StatCard label="Settled"               value={String(settled)}             color="green" sub={`${totalCases ? Math.round(settled/totalCases*100) : 0}% of total`} />
          <StatCard label="Awaiting Settlement"   value={String(pendingSettlement)}   color="amber" sub="Discharged, not settled" />
          <StatCard label="Total Estimated Value" value={inr(totalEstimated)}         color="blue"  sub="Across all pre-auths" />
        </div>

        {/* Pipeline summary */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
            <TrendingUp size={15} className="text-emerald-500" />
            Pipeline Breakdown
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Pre-Auth only',         count: preAuthOnly,         icon: <Clock size={16} />,         color: 'text-slate-500' },
              { label: 'Enhanced',              count: cases.filter(c => c.has_enhancement && !c.has_discharge).length, icon: <AlertCircle size={16} />,    color: 'text-blue-500' },
              { label: 'Discharged',            count: pendingSettlement,    icon: <Briefcase size={16} />,    color: 'text-amber-500' },
              { label: 'Settled',               count: settled,              icon: <CheckCircle2 size={16} />, color: 'text-green-500' },
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    <th className="text-left px-5 py-3">Bill No</th>
                    <th className="text-left px-5 py-3">Patient</th>
                    <th className="text-left px-5 py-3 hidden md:table-cell">Hospital</th>
                    <th className="text-left px-5 py-3">Status</th>
                    <th className="text-right px-5 py-3">Est. Amount</th>
                    <th className="text-left px-5 py-3 hidden lg:table-cell">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c, idx) => {
                    const status = statusOf(c);
                    return (
                      <tr
                        key={c.bill_no}
                        className={`transition-colors ${idx < cases.length - 1 ? 'border-b border-slate-100 dark:border-slate-800' : ''}`}
                      >
                        <td className="px-5 py-3.5">
                          <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1 rounded-lg">
                            {c.bill_no}
                          </span>
                        </td>
                        <td className="px-5 py-3.5">
                          <p className="font-medium text-slate-800 dark:text-slate-200">{c.patient_name || <span className="text-slate-400 italic">Unknown</span>}</p>
                          {c.abha_id && <p className="text-xs text-slate-400 mt-0.5">{c.abha_id}</p>}
                        </td>
                        <td className="px-5 py-3.5 hidden md:table-cell text-slate-500 dark:text-slate-400 text-xs">{c.hospital_name || '—'}</td>
                        <td className="px-5 py-3.5">
                          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusColor(status)}`}>{status}</span>
                        </td>
                        <td className="px-5 py-3.5 text-right font-semibold text-slate-700 dark:text-slate-300 tabular-nums">
                          {inr(c.total_estimated_cost)}
                        </td>
                        <td className="px-5 py-3.5 hidden lg:table-cell text-xs text-slate-400">
                          {c.created_at ? new Date(c.created_at).toLocaleDateString('en-IN') : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                {/* Totals row */}
                {totalEstimated > 0 && (
                  <tfoot>
                    <tr className="border-t-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                      <td colSpan={4} className="px-5 py-3 text-xs font-bold text-slate-500 uppercase tracking-wide">Total Estimated</td>
                      <td className="px-5 py-3 text-right font-extrabold text-slate-800 dark:text-slate-200 tabular-nums text-sm">
                        {inr(totalEstimated)}
                      </td>
                      <td className="hidden lg:table-cell" />
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          )}
        </div>

        {/* MIS Report cards */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
            <Download size={15} className="text-blue-500" />
            MIS Reports
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {([
              { period: 'weekly',  label: 'Weekly Report',  sub: 'Last 7 days' },
              { period: 'monthly', label: 'Monthly Report', sub: 'Last 30 days' },
              { period: 'yearly',  label: 'Yearly Report',  sub: 'Last 365 days' },
            ] as const).map(({ period, label, sub }) => (
              <DownloadCard key={period} period={period} label={label} sub={sub} />
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

function DownloadCard({ period, label, sub }: { period: 'weekly' | 'monthly' | 'yearly'; label: string; sub: string }) {
  const [loading, setLoading] = useState(false);
  const go = async () => {
    setLoading(true);
    try { await downloadMisReport(period); }
    catch (e: any) { alert(e.message || 'Failed'); }
    finally { setLoading(false); }
  };
  return (
    <button
      onClick={go}
      disabled={loading}
      className="flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all text-left group disabled:opacity-60"
    >
      <div>
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 transition-colors">{label}</p>
        <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
      </div>
      {loading
        ? <span className="w-4 h-4 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin shrink-0" />
        : <Download size={16} className="text-slate-300 dark:text-slate-600 group-hover:text-blue-500 transition-colors shrink-0" />
      }
    </button>
  );
}

import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Briefcase, Download, ChevronDown } from 'lucide-react';
import { listCases, downloadMisReport } from '../services/api';
import type { CaseSummary } from '../types/api';

function StepDot({ done, label }: { done: boolean; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`w-3 h-3 rounded-full transition-colors ${
          done ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
        }`}
        title={label}
      />
      <span className="text-xs text-slate-400 dark:text-slate-500 hidden sm:block whitespace-nowrap">{label}</span>
    </div>
  );
}

function FinanceDot({ status }: { status?: string }) {
  const approved = status === 'finance_approved' || status === 'closed' || status === 'followed_up';
  const denied   = status === 'finance_denied';
  const dotCls = approved
    ? 'bg-blue-500'
    : denied
    ? 'bg-red-500'
    : 'bg-slate-300 dark:bg-slate-600';
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`w-3 h-3 rounded-full transition-colors ${dotCls}`} title="Finance" />
      <span className="text-xs text-slate-400 dark:text-slate-500 hidden sm:block whitespace-nowrap">Finance</span>
    </div>
  );
}

function StepIndicators({ c }: { c: CaseSummary }) {
  return (
    <div className="flex items-end gap-3">
      <StepDot done={true} label="Pre-Auth" />
      <StepDot done={c.has_enhancement} label="Enhance" />
      <StepDot done={c.has_discharge} label="Discharge" />
      <StepDot done={c.has_settlement} label="Settlement" />
      <FinanceDot status={c.settlement_status} />
    </div>
  );
}

export default function CaseList() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [misOpen, setMisOpen] = useState(false);
  const [misLoading, setMisLoading] = useState(false);
  const misRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (misRef.current && !misRef.current.contains(e.target as Node)) setMisOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleMisDownload = async (period: 'weekly' | 'monthly' | 'yearly') => {
    setMisOpen(false);
    setMisLoading(true);
    try {
      await downloadMisReport(period);
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Failed to generate MIS report');
    } finally {
      setMisLoading(false);
    }
  };

  useEffect(() => {
    listCases()
      .then(setCases)
      .catch((e) => setError(e.response?.data?.detail || e.message || 'Failed to load cases'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = cases.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (c.bill_no || '').toLowerCase().includes(q) ||
      (c.patient_name || '').toLowerCase().includes(q) ||
      (c.hospital_name || '').toLowerCase().includes(q)
    );
  });

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-xl shadow-lg shadow-emerald-500/20">
            <Briefcase className="text-white" size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">All Cases</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Cashless hospitalization lifecycle</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* MIS Report dropdown */}
          <div ref={misRef} className="relative">
            <button
              onClick={() => setMisOpen(o => !o)}
              disabled={misLoading}
              className="flex items-center gap-1.5 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-medium rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm disabled:opacity-50"
            >
              {misLoading
                ? <span className="w-3.5 h-3.5 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
                : <Download size={15} />}
              MIS Report
              <ChevronDown size={13} className={`transition-transform duration-150 ${misOpen ? 'rotate-180' : ''}`} />
            </button>
            {misOpen && (
              <div className="absolute right-0 mt-1.5 w-36 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg z-20 overflow-hidden">
                {(['weekly', 'monthly', 'yearly'] as const).map(p => (
                  <button
                    key={p}
                    onClick={() => handleMisDownload(p)}
                    className="w-full text-left px-4 py-2.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 capitalize transition-colors"
                  >
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
            )}
          </div>

          <Link
            to="/pre-auth"
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm"
          >
            <Plus size={16} />
            New Pre-Auth
          </Link>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search by Bill No, patient name, or hospital..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        />
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-4 border-emerald-200 border-t-emerald-500 rounded-full animate-spin" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 dark:text-slate-500">
          <Briefcase size={40} className="mb-4 opacity-40" />
          <p className="text-lg font-medium">
            {cases.length === 0 ? 'No cases yet' : 'No cases match your search'}
          </p>
          {cases.length === 0 && (
            <p className="text-sm mt-1">Create a Pre-Auth to start a new case</p>
          )}
        </div>
      )}

      {/* Table */}
      {!loading && !error && filtered.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                <th className="text-left px-5 py-3 font-semibold text-slate-500 dark:text-slate-400">Bill No</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-500 dark:text-slate-400">Patient</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-500 dark:text-slate-400 hidden md:table-cell">Hospital</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-500 dark:text-slate-400">Steps</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-500 dark:text-slate-400 hidden lg:table-cell">Estimate</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-500 dark:text-slate-400 hidden lg:table-cell">Created</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, idx) => (
                <tr
                  key={c.bill_no}
                  onClick={() => navigate(`/cases/${encodeURIComponent(c.bill_no)}`)}
                  className={`cursor-pointer transition-colors hover:bg-blue-50 dark:hover:bg-blue-900/10 ${
                    idx < filtered.length - 1 ? 'border-b border-slate-100 dark:border-slate-800' : ''
                  }`}
                >
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1 rounded-lg whitespace-nowrap">
                      {c.bill_no}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="font-medium text-slate-900 dark:text-white">
                      {c.patient_name || <span className="text-slate-400 italic">Unknown</span>}
                    </div>
                    {c.abha_id && (
                      <div className="text-xs text-slate-400 mt-0.5">{c.abha_id}</div>
                    )}
                  </td>
                  <td className="px-5 py-4 hidden md:table-cell text-slate-600 dark:text-slate-400">
                    {c.hospital_name || '—'}
                  </td>
                  <td className="px-5 py-4">
                    <StepIndicators c={c} />
                  </td>
                  <td className="px-5 py-4 hidden lg:table-cell text-slate-700 dark:text-slate-300">
                    {c.total_estimated_cost != null
                      ? `₹${c.total_estimated_cost.toLocaleString('en-IN')}`
                      : '—'}
                  </td>
                  <td className="px-5 py-4 hidden lg:table-cell text-slate-400 text-xs">
                    {c.created_at ? new Date(c.created_at).toLocaleDateString('en-IN') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

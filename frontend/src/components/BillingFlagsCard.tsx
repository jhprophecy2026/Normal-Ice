import React, { useState, useEffect } from 'react';
import { AlertTriangle, XCircle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';
import { getPatientFlags } from '../services/api';
import type { FlagsResponse, StoredBillingFlag } from '../types/api';

interface BillingFlagsCardProps {
  patientId: string;
}

const BillingFlagsCard: React.FC<BillingFlagsCardProps> = ({ patientId }) => {
  const [data, setData] = useState<FlagsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getPatientFlags(patientId);
      setData(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load claim readiness');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [patientId]);

  const criticalFlags = data?.flags.filter(f => f.severity === 'critical') ?? [];
  const warningFlags  = data?.flags.filter(f => f.severity === 'warning')  ?? [];

  const FlagRow: React.FC<{ flag: StoredBillingFlag }> = ({ flag }) => (
    <div className={`flex gap-3 p-3 rounded-lg border ${
      flag.severity === 'critical'
        ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
        : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
    }`}>
      {flag.severity === 'critical'
        ? <XCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
        : <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />
      }
      <div className="min-w-0">
        <div className={`text-xs font-bold uppercase tracking-wide mb-0.5 ${
          flag.severity === 'critical'
            ? 'text-red-600 dark:text-red-400'
            : 'text-amber-600 dark:text-amber-400'
        }`}>
          {flag.field}
        </div>
        <div className="text-sm text-slate-700 dark:text-slate-300">{flag.message}</div>
      </div>
    </div>
  );

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">Claim Readiness</h3>
        <button
          onClick={load}
          disabled={loading}
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {loading && !data && (
        <div className="flex items-center gap-2 text-slate-400 py-4">
          <Loader2 size={18} className="animate-spin" />
          <span className="text-sm">Analysing…</span>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 py-2">{error}</div>
      )}

      {data && (
        <>
          {/* Score banner */}
          <div className={`flex items-center gap-3 p-4 rounded-xl mb-5 ${
            data.claim_ready
              ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800'
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
          }`}>
            {data.claim_ready
              ? <CheckCircle2 size={24} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
              : <XCircle size={24} className="text-red-500 shrink-0" />
            }
            <div>
              <div className={`font-bold ${
                data.claim_ready
                  ? 'text-emerald-800 dark:text-emerald-200'
                  : 'text-red-800 dark:text-red-200'
              }`}>
                {data.claim_ready ? 'Claim Ready' : 'Not Ready to Submit'}
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400">
                {data.critical_count} critical · {data.warning_count} warning
              </div>
            </div>
          </div>

          {/* Flags */}
          {data.flags.length === 0 ? (
            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-sm">
              <CheckCircle2 size={16} />
              <span>All required billing fields are present.</span>
            </div>
          ) : (
            <div className="space-y-3">
              {criticalFlags.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                    Critical ({criticalFlags.length})
                  </p>
                  <div className="space-y-2">
                    {criticalFlags.map((f, i) => <FlagRow key={i} flag={f} />)}
                  </div>
                </div>
              )}
              {warningFlags.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 mt-4">
                    Warnings ({warningFlags.length})
                  </p>
                  <div className="space-y-2">
                    {warningFlags.map((f, i) => <FlagRow key={i} flag={f} />)}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default BillingFlagsCard;

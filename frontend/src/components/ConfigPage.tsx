import { useState, useEffect, useRef } from 'react';
import { Upload, Save, RotateCcw, CheckCircle2, AlertCircle, Download, ChevronDown } from 'lucide-react';
import { getCostEstimates, updateCostEstimates, uploadCostEstimatesFile } from '../services/api';

const BTN = "flex items-center justify-center gap-1.5 w-28 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors";

export default function ConfigPage() {
  const [raw, setRaw]           = useState('');
  const [meta, setMeta]         = useState<any>(null);
  const [saving, setSaving]     = useState(false);
  const [loading, setLoading]   = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [parseErr, setParseErr] = useState<string | null>(null);
  const [status, setStatus]     = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getCostEstimates();
      setMeta(res._meta ?? null);
      setRaw(JSON.stringify(res.data, null, 2));
    } catch {
      setStatus({ type: 'error', msg: 'Failed to load cost estimates from server.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const validate = (text: string): any[] | null => {
    try {
      const parsed = JSON.parse(text);
      if (!Array.isArray(parsed)) { setParseErr('Must be a JSON array [ ... ]'); return null; }
      setParseErr(null);
      return parsed;
    } catch (e: any) {
      setParseErr(e.message);
      return null;
    }
  };

  const handleChange = (val: string) => { setRaw(val); validate(val); };

  const handleSave = async () => {
    const parsed = validate(raw);
    if (!parsed) return;
    setSaving(true); setStatus(null);
    try {
      const res = await updateCostEstimates(parsed);
      setStatus({ type: 'success', msg: `Saved ${res.count} entries successfully.` });
    } catch (e: any) {
      setStatus({ type: 'error', msg: e.response?.data?.detail || e.message || 'Save failed' });
    } finally {
      setSaving(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    setStatus(null);
    try {
      const res = await uploadCostEstimatesFile(file);
      setStatus({ type: 'success', msg: `Uploaded ${res.count} entries.` });
      await load();
    } catch (e: any) {
      setStatus({ type: 'error', msg: e.response?.data?.detail || e.message || 'Upload failed' });
    }
  };

  const handleDownload = () => {
    const blob = new Blob([raw], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'disease_cost_estimates.json'; a.click();
    URL.revokeObjectURL(url);
  };

  const entryCount = (() => { try { const p = JSON.parse(raw); return Array.isArray(p) ? p.length : null; } catch { return null; } })();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Configure</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Manage system configuration and reference data.</p>
      </div>

      {/* Cost Estimates card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">

        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Disease Cost Estimates</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Used to auto-fill cost fields in Pre-Authorization forms.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={() => fileRef.current?.click()} className={BTN}><Upload size={13} /> Upload</button>
            <input ref={fileRef} type="file" accept=".json" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); e.target.value = ''; }} />
            <button onClick={handleDownload} className={BTN}><Download size={13} /> Export</button>
            <button onClick={load} className={BTN}><RotateCcw size={13} /> Reset</button>
          </div>
        </div>

        {/* Data sources + notes */}
        {meta && (
          <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 space-y-3 text-xs text-slate-500 dark:text-slate-400">
            {/* Sources — hospital/org names only, plain list */}
            {meta.sources?.length > 0 && (
              <div>
                <p className="font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Data Sources</p>
                <div className="flex flex-wrap gap-2">
                  {meta.sources.map((s: string, i: number) => (
                    <span key={i} className="px-2.5 py-1 rounded-full bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 font-medium">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Notes — collapsible */}
            {meta.notes?.length > 0 && (
              <details className="group">
                <summary className="cursor-pointer select-none font-semibold text-slate-600 dark:text-slate-300 flex items-center gap-1 list-none">
                  <ChevronDown size={13} className="transition-transform group-open:rotate-180" />
                  Notes
                </summary>
                <ul className="mt-1.5 ml-4 space-y-0.5 list-disc list-inside">
                  {meta.notes.map((n: string, i: number) => <li key={i}>{n}</li>)}
                </ul>
              </details>
            )}
          </div>
        )}

        {/* Status banner */}
        {status && (
          <div className={`px-6 py-3 flex items-center gap-2 text-sm ${
            status.type === 'success'
              ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300'
              : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300'
          }`}>
            {status.type === 'success' ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
            {status.msg}
          </div>
        )}

        {/* JSON editor — collapsible */}
        <div>
          <button
            onClick={() => setEditorOpen(o => !o)}
            className="w-full flex items-center justify-between px-6 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors text-left"
          >
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Edit JSON Data {entryCount !== null && <span className="text-xs text-slate-400 font-normal ml-1">({entryCount} entries)</span>}
            </span>
            <ChevronDown size={16} className={`text-slate-400 transition-transform duration-200 ${editorOpen ? 'rotate-180' : ''}`} />
          </button>

          {editorOpen && (
            <div className="px-6 pb-6">
              {loading ? (
                <div className="flex items-center justify-center h-40 text-slate-400 text-sm">Loading...</div>
              ) : (
                <>
                  <textarea
                    value={raw}
                    onChange={(e) => handleChange(e.target.value)}
                    spellCheck={false}
                    className={`w-full h-[520px] font-mono text-xs rounded-xl border px-4 py-3 bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 resize-none focus:outline-none focus:ring-2 transition-colors ${
                      parseErr
                        ? 'border-red-400 dark:border-red-600 focus:ring-red-400/30'
                        : 'border-slate-200 dark:border-slate-700 focus:ring-blue-400/30'
                    }`}
                  />
                  {parseErr && (
                    <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle size={12} /> {parseErr}
                    </p>
                  )}
                  <div className="mt-4 flex items-center justify-end">
                    <button
                      onClick={handleSave}
                      disabled={saving || !!parseErr || loading}
                      className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                      {saving
                        ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        : <Save size={14} />}
                      Save Changes
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

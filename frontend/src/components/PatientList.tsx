import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User, FileText, ChevronRight, AlertCircle, Loader2 } from 'lucide-react';
import { getPatients } from '../services/api';
import type { PatientSummary } from '../types/api';

const PatientList: React.FC = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPatients = useCallback(async (query: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPatients(query || undefined);
      setPatients(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchPatients('');
  }, [fetchPatients]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => fetchPatients(search), 350);
    return () => clearTimeout(timer);
  }, [search, fetchPatients]);

  const formatDate = (iso: string) => {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white mb-2">Patient Records</h1>
        <p className="text-slate-500 dark:text-slate-400">Search and manage all stored patient data</p>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search by name, ABHA ID, or patient ID…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-11 pr-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-colors"
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={28} className="animate-spin mr-3" />
          <span>Loading patients…</span>
        </div>
      ) : error ? (
        <div className="flex items-center gap-3 p-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      ) : patients.length === 0 ? (
        <div className="text-center py-20 text-slate-400 dark:text-slate-500">
          <User size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">
            {search ? 'No patients match your search' : 'No patients stored yet'}
          </p>
          <p className="text-sm mt-1">
            {!search && 'Upload a clinical PDF to create a patient record.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            {patients.length} patient{patients.length !== 1 ? 's' : ''} found
          </p>
          {patients.map(patient => (
            <button
              key={patient.patient_id}
              onClick={() => navigate(`/patients/${patient.patient_id}`)}
              className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 flex items-center justify-between gap-4 hover:shadow-md hover:border-emerald-300 dark:hover:border-emerald-700 transition-all text-left group"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="bg-emerald-100 dark:bg-emerald-900/40 p-3 rounded-xl shrink-0">
                  <User size={20} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-slate-900 dark:text-white text-base truncate">
                    {patient.name || 'Unknown Patient'}
                  </div>
                  <div className="text-sm text-slate-500 dark:text-slate-400 truncate">
                    {patient.abha_id
                      ? `ABHA: ${patient.abha_id}`
                      : `ID: ${patient.patient_id}`}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-6 shrink-0">
                <div className="hidden sm:flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400">
                  <FileText size={14} />
                  <span>{patient.document_count} doc{patient.document_count !== 1 ? 's' : ''}</span>
                </div>
                <div className="hidden md:block text-sm text-slate-400 dark:text-slate-500 whitespace-nowrap">
                  {formatDate(patient.last_updated)}
                </div>
                <ChevronRight
                  size={18}
                  className="text-slate-300 dark:text-slate-600 group-hover:text-emerald-500 transition-colors"
                />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default PatientList;

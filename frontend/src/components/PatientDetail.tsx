import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, User, FlaskConical, Pill, FileText, AlertCircle, Loader2, Trash2,
} from 'lucide-react';
import { getPatient, deletePatient } from '../services/api';
import type { StoredPatientRecord } from '../types/api';
import JsonViewer from './JsonViewer';
import BillingFlagsCard from './BillingFlagsCard';

type Tab = 'overview' | 'labs' | 'meds' | 'bundles' | 'docs';

const PatientDetail: React.FC = () => {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<StoredPatientRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!patientId) return;
    setLoading(true);
    setError(null);
    getPatient(patientId)
      .then(setPatient)
      .catch(err => setError(err.response?.data?.detail || err.message || 'Failed to load patient'))
      .finally(() => setLoading(false));
  }, [patientId]);

  const handleDelete = async () => {
    if (!patientId || !window.confirm('Delete this patient record? This cannot be undone.')) return;
    setDeleting(true);
    try {
      await deletePatient(patientId);
      navigate('/patients');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Delete failed');
      setDeleting(false);
    }
  };

  const formatDate = (iso?: string) => {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return iso; }
  };

  const Tab = ({ id, label, count }: { id: Tab; label: string; count?: number }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`px-5 py-3 font-semibold text-sm transition-all relative whitespace-nowrap ${
        activeTab === id
          ? 'text-emerald-600 dark:text-emerald-400'
          : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
      }`}
    >
      {label}
      {count !== undefined && count > 0 && (
        <span className="ml-1.5 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400 text-xs font-bold px-1.5 py-0.5 rounded-full">
          {count}
        </span>
      )}
      {activeTab === id && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600 dark:bg-emerald-400" />
      )}
    </button>
  );

  if (loading) return (
    <div className="flex items-center justify-center py-32 text-slate-400">
      <Loader2 size={28} className="animate-spin mr-3" />
      <span>Loading patient record…</span>
    </div>
  );

  if (error) return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 p-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400">
        <AlertCircle size={20} />
        <span>{error}</span>
      </div>
      <button onClick={() => navigate('/patients')} className="mt-4 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-1">
        <ChevronLeft size={16} /> Back to patients
      </button>
    </div>
  );

  if (!patient) return null;

  return (
    <div className="max-w-5xl mx-auto">
      {/* Back + Delete */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate('/patients')}
          className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
        >
          <ChevronLeft size={16} /> All Patients
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="flex items-center gap-1.5 text-sm text-red-500 hover:text-red-700 dark:hover:text-red-400 transition-colors disabled:opacity-50"
        >
          <Trash2 size={15} /> {deleting ? 'Deleting…' : 'Delete Patient'}
        </button>
      </div>

      {/* Patient header */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="bg-emerald-100 dark:bg-emerald-900/40 p-4 rounded-xl shrink-0">
            <User size={28} className="text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white mb-1">
              {patient.name || 'Unknown Patient'}
            </h1>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
              {patient.abha_id && <span>ABHA: <strong className="text-slate-700 dark:text-slate-300">{patient.abha_id}</strong></span>}
              {patient.age != null && <span>Age: <strong className="text-slate-700 dark:text-slate-300">{patient.age}</strong></span>}
              {patient.gender && <span>Gender: <strong className="text-slate-700 dark:text-slate-300 capitalize">{patient.gender}</strong></span>}
              {patient.date_of_birth && <span>DOB: <strong className="text-slate-700 dark:text-slate-300">{patient.date_of_birth}</strong></span>}
              {patient.contact && <span>Contact: <strong className="text-slate-700 dark:text-slate-300">{patient.contact}</strong></span>}
            </div>
            {(patient.practitioner_name || patient.organization_name) && (
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-500 dark:text-slate-400 mt-1">
                {patient.practitioner_name && <span>Provider: <strong className="text-slate-700 dark:text-slate-300">{patient.practitioner_name}</strong></span>}
                {patient.organization_name && <span>Org: <strong className="text-slate-700 dark:text-slate-300">{patient.organization_name}</strong></span>}
              </div>
            )}
          </div>
          <div className="text-right text-xs text-slate-400 dark:text-slate-500 shrink-0">
            <div>Created {formatDate(patient.created_at)}</div>
            <div>Updated {formatDate(patient.updated_at)}</div>
          </div>
        </div>
      </div>

      {/* Main + Sidebar grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main panel */}
        <div className="lg:col-span-2">
          {/* Tabs */}
          <div className="flex gap-0 border-b border-slate-200 dark:border-slate-700 mb-5 overflow-x-auto">
            <Tab id="overview" label="Overview" />
            <Tab id="labs"     label="Labs"     count={patient.observations.length} />
            <Tab id="meds"     label="Meds"     count={patient.medications.length} />
            <Tab id="bundles"  label="FHIR Bundles" count={patient.fhir_bundles.length} />
            <Tab id="docs"     label="Documents" count={patient.documents.length} />
          </div>

          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6">
            {/* Overview */}
            {activeTab === 'overview' && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Diagnoses</h4>
                  {patient.diagnoses.length === 0
                    ? <p className="text-slate-400 dark:text-slate-500 text-sm">None recorded</p>
                    : (
                      <div className="flex flex-wrap gap-2">
                        {patient.diagnoses.map((d, i) => (
                          <span key={i} className="bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 px-3 py-1 rounded-full text-sm">
                            {d}
                          </span>
                        ))}
                      </div>
                    )
                  }
                </div>
                <div className="grid grid-cols-3 gap-4 pt-2">
                  {[
                    { label: 'Lab Results', value: patient.observations.length, icon: <FlaskConical size={20} className="text-blue-500" /> },
                    { label: 'Medications', value: patient.medications.length, icon: <Pill size={20} className="text-purple-500" /> },
                    { label: 'Documents', value: patient.documents.length, icon: <FileText size={20} className="text-emerald-500" /> },
                  ].map(item => (
                    <div key={item.label} className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4 flex items-center gap-3">
                      {item.icon}
                      <div>
                        <div className="text-xl font-bold text-slate-900 dark:text-white">{item.value}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">{item.label}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Labs */}
            {activeTab === 'labs' && (
              patient.observations.length === 0
                ? <p className="text-slate-400 dark:text-slate-500 text-sm">No lab results recorded</p>
                : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
                          <th className="pb-3 pr-4">Test</th>
                          <th className="pb-3 pr-4">Value</th>
                          <th className="pb-3 pr-4">Unit</th>
                          <th className="pb-3 pr-4">Reference</th>
                          <th className="pb-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                        {patient.observations.map((obs: any, i: number) => (
                          <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                            <td className="py-3 pr-4 font-medium text-slate-900 dark:text-white">{obs.test_name}</td>
                            <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{obs.value ?? '—'}</td>
                            <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">{obs.unit ?? '—'}</td>
                            <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">{obs.reference_range ?? '—'}</td>
                            <td className="py-3">
                              <span className="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400 text-xs px-2 py-0.5 rounded-full">
                                {obs.status ?? 'final'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
            )}

            {/* Medications */}
            {activeTab === 'meds' && (
              patient.medications.length === 0
                ? <p className="text-slate-400 dark:text-slate-500 text-sm">No medications recorded</p>
                : (
                  <div className="space-y-3">
                    {patient.medications.map((med: any, i: number) => (
                      <div key={i} className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4">
                        <div className="font-semibold text-slate-900 dark:text-white mb-1">{med.medication_name}</div>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
                          {med.dosage && <span>Dose: {med.dosage}</span>}
                          {med.frequency && <span>Freq: {med.frequency}</span>}
                          {med.duration && <span>Duration: {med.duration}</span>}
                          {med.route && <span>Route: {med.route}</span>}
                        </div>
                        {med.instructions && (
                          <div className="text-sm text-slate-500 dark:text-slate-400 mt-1 italic">{med.instructions}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )
            )}

            {/* FHIR Bundles */}
            {activeTab === 'bundles' && (
              patient.fhir_bundles.length === 0
                ? <p className="text-slate-400 dark:text-slate-500 text-sm">No FHIR bundles generated yet</p>
                : (
                  <div className="space-y-4">
                    {patient.fhir_bundles.map((bundle: any, i: number) => (
                      <div key={i}>
                        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                          Bundle #{patient.fhir_bundles.length - i}
                        </p>
                        <JsonViewer data={bundle} />
                      </div>
                    ))}
                  </div>
                )
            )}

            {/* Documents */}
            {activeTab === 'docs' && (
              patient.documents.length === 0
                ? <p className="text-slate-400 dark:text-slate-500 text-sm">No documents uploaded</p>
                : (
                  <div className="space-y-3">
                    {patient.documents.map((doc, i) => (
                      <div key={i} className="flex items-center gap-4 bg-slate-50 dark:bg-slate-900 rounded-xl p-4">
                        <FileText size={20} className="text-emerald-500 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-slate-900 dark:text-white truncate">{doc.filename}</div>
                          <div className="text-sm text-slate-500 dark:text-slate-400">
                            {doc.document_type.replace('_', ' ')} · {formatDate(doc.upload_date)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )
            )}
          </div>
        </div>

        {/* Sidebar — Claim Readiness */}
        <div className="lg:col-span-1">
          <BillingFlagsCard patientId={patient.patient_id} />
        </div>
      </div>
    </div>
  );
};

export default PatientDetail;

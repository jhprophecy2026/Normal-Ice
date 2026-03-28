import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Upload, CheckCircle2, AlertTriangle, AlertCircle,
  Download, Plus, ArrowLeft, ArrowRight, IndianRupee, FileText, Lock, Send,
} from 'lucide-react';
import {
  getCase, generatePreAuthPdf, createEnhancement,
  createDischarge, extractDischargeData, updateDischarge,
  createSettlement, updateSettlement,
} from '../services/api';
import type {
  CaseDetail, EnhancementData, DischargeData, DischargeResponse,
  SettlementResponse,
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
    draft:     'bg-slate-700 text-slate-300',
    submitted: 'bg-blue-900/60 text-blue-300',
    pending:   'bg-amber-900/60 text-amber-300',
    approved:  'bg-emerald-900/60 text-emerald-300',
    rejected:  'bg-red-900/60 text-red-300',
    paid:      'bg-purple-900/60 text-purple-300',
  };
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full capitalize ${map[status] ?? map.pending}`}>
      {status}
    </span>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs text-slate-500 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-slate-200">{value || '—'}</p>
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
    'w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-800 text-sm text-slate-100 ' +
    'placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-colors';
  return (
    <div className={span2 ? 'col-span-2' : ''}>
      <label className="block text-xs font-semibold text-slate-400 mb-1">{label}</label>
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
    <div className="flex items-start mb-10">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-start flex-1 min-w-0">
          {/* Circle + label */}
          <div className="flex flex-col items-center flex-shrink-0">
            <button
              onClick={() => step.status !== 'locked' && onStepClick(step.id)}
              disabled={step.status === 'locked'}
              className={[
                'w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-200 focus:outline-none',
                step.status === 'done'
                  ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                  : step.status === 'active'
                  ? 'bg-slate-600 text-white ring-2 ring-emerald-400 ring-offset-2 ring-offset-slate-950'
                  : step.status === 'locked'
                  ? 'bg-slate-800 text-slate-600 cursor-not-allowed border border-slate-700'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600 cursor-pointer',
              ].join(' ')}
            >
              {step.status === 'done' ? <CheckCircle2 size={20} /> : step.status === 'locked' ? <Lock size={14} /> : step.id}
            </button>
            <span className={`text-xs mt-2 font-medium text-center whitespace-nowrap ${
              step.status === 'active' ? 'text-white' :
              step.status === 'done'   ? 'text-emerald-400' :
              step.status === 'locked' ? 'text-slate-600' :
              'text-slate-400'
            }`}>
              {step.label}
            </span>
          </div>

          {/* Connector line (not after last) */}
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mt-5 mx-2 rounded-full transition-colors ${
              step.status === 'done' ? 'bg-emerald-500' : 'bg-slate-700'
            }`} />
          )}
        </div>
      ))}
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
  if (!pa) return <p className="text-slate-400 text-sm">No pre-auth data.</p>;

  const isAlreadySubmitted = pa.status === 'submitted' || pa.status === 'approved';

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      // Generate + download the PDF (which also sets status → submitted on backend)
      const blob = await generatePreAuthPdf(pa.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pre_auth_${pa.id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setSubmitted(true);
      // Advance to Enhancement step after a short moment so user sees the success state
      setTimeout(onNext, 800);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Already-submitted banner */}
      {isAlreadySubmitted && (
        <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-sm">
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

      <div className="h-px bg-slate-800" />

      <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
        <Info label="Hospital"           value={pa.hospital_name} />
        <Info label="ROHINI ID"          value={pa.rohini_id} />
        <Info label="Doctor"             value={pa.doctor_name} />
        <Info label="Admission Date"     value={pa.admission_date} />
        <Info label="Admission Type"     value={pa.admission_type} />
        <Info label="Room Type"          value={pa.room_type} />
      </div>

      <div className="h-px bg-slate-800" />

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

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2 flex-wrap">
        {/* Primary: Submit to TPA (generates PDF + advances step) */}
        {!isAlreadySubmitted && (
          <button
            onClick={handleSubmit}
            disabled={submitting || submitted}
            className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60"
          >
            {submitting ? <Spinner sm /> : submitted ? <CheckCircle2 size={14} /> : <Send size={14} />}
            {submitting ? 'Generating & Submitting…' : submitted ? 'Submitted!' : 'Submit Pre-Auth to TPA'}
          </button>
        )}

        {/* Secondary: just download without advancing */}
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
          className="flex items-center gap-2 px-5 py-2.5 border border-slate-700 text-slate-300 text-sm font-semibold rounded-xl hover:bg-slate-800 transition-colors"
        >
          <Download size={14} />
          Download PDF
        </button>

        {/* If already submitted, show a "Next: Enhancement" button */}
        {isAlreadySubmitted && (
          <button
            onClick={onNext}
            className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            Next: Enhancement <ArrowRight size={14} />
          </button>
        )}

        {pa.patient_id && (
          <Link
            to={`/patients/${pa.patient_id}`}
            className="flex items-center gap-2 px-5 py-2.5 border border-slate-700 text-slate-300 text-sm font-semibold rounded-xl hover:bg-slate-800 transition-colors"
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

function EnhancementContent({
  caseData, onRefresh,
}: {
  caseData: CaseDetail;
  onRefresh: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Partial<EnhancementData>>({});
  const [err, setErr] = useState<string | null>(null);

  const pa = caseData.pre_auth;
  const enhancements = caseData.enhancements || [];

  const set = (k: keyof EnhancementData, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async () => {
    if (!pa) return;
    if (!form.reason?.trim()) { setErr('Reason is required'); return; }
    setSaving(true); setErr(null);
    try {
      await createEnhancement(pa.id, { ...form, pre_auth_id: pa.id, reason: form.reason! });
      setShowForm(false);
      setForm({});
      onRefresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Info banner */}
      <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-slate-800 border border-slate-700 text-sm text-slate-400">
        <AlertCircle size={15} className="mt-0.5 shrink-0 text-amber-400" />
        Enhancement is <span className="text-slate-200 font-medium mx-1">optional</span>. Raise one if the diagnosis or treatment plan changes after the initial pre-auth.
      </div>

      {/* Existing enhancements */}
      {enhancements.length === 0 && !showForm && (
        <p className="text-slate-500 text-sm py-2">No enhancements raised yet for this case.</p>
      )}

      {enhancements.map((e) => (
        <div key={e.id} className="p-4 bg-slate-800 rounded-xl border border-slate-700 text-sm">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
              {e.sequence_no}
            </span>
            <Badge status={e.status} />
            {e.original_diagnosis && (
              <span className="text-xs text-slate-500 ml-auto">
                Original: {e.original_diagnosis}
              </span>
            )}
          </div>
          <p className="font-semibold text-slate-200 mb-1">{e.reason}</p>
          {e.clinical_justification && (
            <p className="text-slate-400 text-xs mb-2">{e.clinical_justification}</p>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
            {e.updated_diagnosis && (
              <Info label="Updated Diagnosis" value={e.updated_diagnosis} />
            )}
            {e.updated_icd10_code && (
              <Info label="Updated ICD-10" value={e.updated_icd10_code} />
            )}
            {e.revised_total_estimated_cost != null && (
              <Info label="Revised Cost" value={fmt(e.revised_total_estimated_cost)} />
            )}
          </div>
          {e.original_total_cost != null && e.revised_total_estimated_cost != null && (
            <div className={`mt-2 text-xs font-semibold ${
              e.revised_total_estimated_cost > e.original_total_cost
                ? 'text-red-400' : 'text-emerald-400'
            }`}>
              {e.revised_total_estimated_cost > e.original_total_cost ? '▲' : '▼'}
              {' '}{fmt(Math.abs(e.revised_total_estimated_cost - e.original_total_cost))} vs original
            </div>
          )}
        </div>
      ))}

      {/* Add form */}
      {showForm && (
        <div className="p-5 bg-slate-800 rounded-xl border border-slate-700">
          <h4 className="text-sm font-semibold text-slate-200 mb-4">
            New Enhancement #{enhancements.length + 1}
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FormInput label="Reason *" value={form.reason || ''} onChange={(v) => set('reason', v)} span2 />
            <FormInput label="Clinical Justification" value={form.clinical_justification || ''} onChange={(v) => set('clinical_justification', v)} span2 area />
            <FormInput label="Updated Diagnosis" value={form.updated_diagnosis || ''} onChange={(v) => set('updated_diagnosis', v)} />
            <FormInput label="Updated ICD-10 Code" value={form.updated_icd10_code || ''} onChange={(v) => set('updated_icd10_code', v)} />
            <FormInput label="Updated Line of Treatment" value={form.updated_line_of_treatment || ''} onChange={(v) => set('updated_line_of_treatment', v)} />
            <FormInput label="Updated Surgery Name" value={form.updated_surgery_name || ''} onChange={(v) => set('updated_surgery_name', v)} />
            <FormInput label="Revised Total Cost (₹)" value={form.revised_total_estimated_cost?.toString() || ''} onChange={(v) => set('revised_total_estimated_cost', v ? Number(v) : undefined)} type="number" />
          </div>
          {err && <p className="text-xs text-red-400 mt-2">{err}</p>}
          <div className="flex gap-2 mt-4">
            <button onClick={handleSubmit} disabled={saving}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60 flex items-center gap-2">
              {saving ? <Spinner sm /> : null} Save Enhancement
            </button>
            <button onClick={() => { setShowForm(false); setErr(null); }}
              className="px-4 py-2 border border-slate-700 text-slate-400 text-sm rounded-xl hover:bg-slate-700 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      )}

      {!showForm && (
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-5 py-2.5 border border-dashed border-slate-700 hover:border-emerald-500 text-slate-400 hover:text-emerald-400 text-sm font-medium rounded-xl transition-colors">
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
      setForm((f) => ({
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
      }));
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
      {/* Revenue flags */}
      {discharge && !editing && (discharge.revenue_flags?.length ?? 0) > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Revenue Reconciliation Flags</p>
          {discharge.revenue_flags.map((flag, i) => (
            <div key={i} className={`flex items-start gap-2 px-4 py-3 rounded-xl text-sm ${
              flag.severity === 'critical'
                ? 'bg-red-950/50 border border-red-800 text-red-300'
                : 'bg-amber-950/50 border border-amber-800 text-amber-300'
            }`}>
              {flag.severity === 'critical'
                ? <AlertCircle size={15} className="shrink-0 mt-0.5" />
                : <AlertTriangle size={15} className="shrink-0 mt-0.5" />}
              <span>{flag.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Summary view */}
      {discharge && !editing && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
            <Info label="Discharge Date"   value={discharge.discharge_date} />
            <Info label="Final Diagnosis"  value={discharge.final_diagnosis} />
            <Info label="ICD-10 Codes"     value={discharge.final_icd10_codes} />
            <Info label="Procedure Codes"  value={discharge.procedure_codes} />
          </div>
          <div className="h-px bg-slate-800" />
          {/* Bill breakdown */}
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Final Bill Breakdown</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Info label="Room Charges"          value={fmt(discharge.room_charges)} />
              <Info label="ICU Charges"           value={fmt(discharge.icu_charges)} />
              <Info label="Surgery Charges"       value={fmt(discharge.surgery_charges)} />
              <Info label="Medicine / Consumables" value={fmt(discharge.medicine_charges)} />
              <Info label="Investigation Charges" value={fmt(discharge.investigation_charges)} />
              <Info label="Other Charges"         value={fmt(discharge.other_charges)} />
            </div>
            <div className="mt-4 flex items-center justify-between px-4 py-3 bg-slate-800 rounded-xl border border-slate-700">
              <span className="text-sm font-semibold text-slate-400">Total Bill Amount</span>
              <span className="text-lg font-bold text-white">{fmt(discharge.total_bill_amount)}</span>
            </div>
          </div>
          <button onClick={() => setEditing(true)}
            className="text-sm text-emerald-400 hover:text-emerald-300 font-medium hover:underline">
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
              ? 'border-emerald-500 bg-emerald-950/20'
              : 'border-slate-700 hover:border-emerald-500 hover:bg-emerald-950/10'
          }`}>
            <input type="file" accept=".pdf" className="hidden" disabled={uploading}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); }} />
            {uploading ? (
              <>
                <div className="w-9 h-9 border-4 border-emerald-700 border-t-emerald-400 rounded-full animate-spin mb-3" />
                <p className="text-sm text-emerald-400 font-medium">Extracting with Gemini AI...</p>
                <p className="text-xs text-slate-500 mt-1">Reading discharge summary, diagnoses, procedure codes &amp; bill</p>
              </>
            ) : (
              <>
                <Upload size={24} className="text-slate-500 mb-3" />
                <p className="text-sm font-semibold text-slate-300">Upload Discharge Summary / Final Bill PDF</p>
                <p className="text-xs text-slate-500 mt-1">Gemini will auto-fill all fields below</p>
              </>
            )}
          </label>

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

          {err && <p className="text-xs text-red-400">{err}</p>}

          <div className="flex gap-3">
            <button onClick={handleSave} disabled={saving}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60 flex items-center gap-2">
              {saving ? <Spinner sm /> : null} Save Discharge
            </button>
            {discharge && (
              <button onClick={() => { setEditing(false); setErr(null); }}
                className="px-4 py-2.5 border border-slate-700 text-slate-400 text-sm rounded-xl hover:bg-slate-800 transition-colors">
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
      <div className="flex items-center gap-3 px-5 py-6 bg-amber-950/30 border border-amber-800 rounded-xl text-amber-300 text-sm">
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
        <div className="flex items-center justify-between px-5 py-4 bg-slate-800 rounded-xl border border-slate-700">
          <div>
            <p className="text-xs text-slate-400 mb-1">Settlement Status</p>
            <Badge status={settlement.status || 'pending'} />
          </div>
          {settlement.final_settlement_amount != null && (
            <div className="text-right">
              <p className="text-xs text-slate-400 mb-1">Final Settlement</p>
              <p className="text-2xl font-bold text-emerald-400">{fmt(settlement.final_settlement_amount)}</p>
            </div>
          )}
        </div>
      )}

      {/* Comparison table */}
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Amount Comparison</p>
        <div className="rounded-xl border border-slate-700 overflow-hidden text-sm">
          <table className="w-full">
            <tbody>
              <tr className="border-b border-slate-800">
                <td className="px-4 py-3.5 text-slate-400">Pre-Auth Estimate</td>
                <td className="px-4 py-3.5 font-semibold text-slate-200 text-right">{fmt(preAuthEstimate)}</td>
              </tr>
              <tr className="border-b border-slate-800">
                <td className="px-4 py-3.5 text-slate-400">Final Bill (Claimed)</td>
                <td className="px-4 py-3.5 font-semibold text-slate-200 text-right">{fmt(claimedAmount)}</td>
              </tr>
              {variance != null && (
                <tr className="border-b border-slate-800">
                  <td className="px-4 py-3.5 text-slate-400">Variance</td>
                  <td className={`px-4 py-3.5 font-semibold text-right ${variance > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                    {variance > 0 ? '▲ +' : '▼ '}{fmt(Math.abs(variance))}
                  </td>
                </tr>
              )}
              <tr>
                <td className="px-4 py-3.5 text-slate-400">Deduction</td>
                <td className="px-4 py-3.5 font-semibold text-right text-amber-400">– {fmt(deductionNum)}</td>
              </tr>
              <tr className="bg-slate-800/60">
                <td className="px-4 py-4 font-bold text-slate-200">Settlement Amount</td>
                <td className="px-4 py-4 font-bold text-emerald-400 text-right text-lg">
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

      {err && <p className="text-xs text-red-400">{err}</p>}

      {/* Action buttons */}
      {!settlement ? (
        <button onClick={handleCreate} disabled={saving}
          className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-60">
          {saving ? <Spinner sm /> : <IndianRupee size={14} />}
          Create Settlement
        </button>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(['approved', 'rejected', 'paid'] as const).map((s) => {
            const labels: Record<string, string> = { approved: '✓ Approve', rejected: '✗ Reject', paid: '💳 Mark Paid' };
            const colors: Record<string, string> = {
              approved: 'bg-emerald-700 hover:bg-emerald-600',
              rejected: 'bg-red-800 hover:bg-red-700',
              paid:     'bg-purple-800 hover:bg-purple-700',
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
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(1);

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
        <div className="w-10 h-10 border-4 border-slate-700 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-6 bg-red-950/30 border border-red-800 rounded-2xl text-red-300">
        <p className="font-semibold">{error || 'Case not found'}</p>
        <Link to="/cases" className="text-sm underline mt-2 inline-block text-red-400">Back to Cases</Link>
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
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={15} /> All Cases
      </Link>

      {/* ── Case header card (dark, matches screenshot) ── */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl px-7 py-6 mb-8 shadow-lg">
        <div className="flex items-center gap-2 mb-4">
          <FileText size={16} className="text-emerald-400" />
          <span className="font-mono text-sm font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full border border-slate-700">
            {caseData.bill_no}
          </span>
          {pa && <Badge status={pa.status} />}
        </div>
        <h1 className="text-3xl font-extrabold text-white mb-1">
          {pa?.patient_name || 'Unknown Patient'}
        </h1>
        <p className="text-slate-400 text-sm">
          {[pa?.hospital_name, pa?.admission_date].filter(Boolean).join(' · ')}
          {pa?.abha_id && (
            <span className="ml-3 text-slate-500">ABHA: {pa.abha_id}</span>
          )}
        </p>
      </div>

      {/* ── Stepper ── */}
      <Stepper steps={steps} activeStep={activeStep} onStepClick={setActiveStep} />

      {/* ── Active step content card ── */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-lg overflow-hidden">
        {/* Step content header */}
        <div className="px-7 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              steps[activeStep - 1].status === 'done'
                ? 'bg-emerald-500 text-white'
                : 'bg-slate-700 text-slate-300'
            }`}>
              {steps[activeStep - 1].status === 'done' ? <CheckCircle2 size={16} /> : activeStep}
            </div>
            <div>
              <h2 className="text-base font-bold text-white">{stepTitles[activeStep]}</h2>
              <p className="text-xs text-slate-500 mt-0.5">{stepDescriptions[activeStep]}</p>
            </div>
            {activeStep === 2 && (
              <span className="ml-auto text-xs px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400">
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
        <div className="px-7 py-4 border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={() => setActiveStep((s) => Math.max(1, s - 1))}
            disabled={activeStep === 1}
            className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ArrowLeft size={14} /> Previous
          </button>
          <span className="text-xs text-slate-600">{activeStep} / 4</span>
          <button
            onClick={() => {
              const next = activeStep + 1;
              if (next <= 4 && steps[next - 1].status !== 'locked') setActiveStep(next);
            }}
            disabled={activeStep === 4 || steps[activeStep].status === 'locked'}
            className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next <ArrowLeft size={14} className="rotate-180" />
          </button>
        </div>
      </div>
    </div>
  );
}

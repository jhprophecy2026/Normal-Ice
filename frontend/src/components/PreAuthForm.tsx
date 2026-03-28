import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Building2, User, Stethoscope, ClipboardList, Calendar,
  IndianRupee, Shield, FileText, Search, Upload, Download,
  ChevronDown, ChevronUp, AlertCircle, CheckCircle2,
  Sparkles, ArrowRight, Loader2,
} from 'lucide-react';
import {
  lookupAbha, createPreAuth, updatePreAuth,
  extractMedicalFromPdf, generatePreAuthPdf,
  estimateCosts,
} from '../services/api';
import type { PreAuthData, AbhaPatient } from '../types/api';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const REQUIRED: Set<keyof PreAuthData> = new Set([
  'patient_name', 'date_of_birth', 'contact', 'policy_no',
  'hospital_name', 'rohini_id', 'doctor_name',
  'presenting_complaints', 'provisional_diagnosis',
  'icd10_diagnosis_code', 'admission_date', 'admission_type',
  'total_estimated_cost',
]);

const FIELD_LABELS: Partial<Record<keyof PreAuthData, string>> = {
  patient_name: 'Patient Name', date_of_birth: 'Date of Birth',
  contact: 'Contact No.', policy_no: 'Policy No.',
  hospital_name: 'Hospital Name', rohini_id: 'ROHINI ID',
  doctor_name: 'Doctor Name', presenting_complaints: 'Presenting Complaints',
  provisional_diagnosis: 'Provisional Diagnosis', icd10_diagnosis_code: 'ICD-10 Code',
  admission_date: 'Admission Date', admission_type: 'Admission Type',
  total_estimated_cost: 'Total Estimated Cost',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
type FieldState = 'required-empty' | 'filled' | 'optional-empty';

function getFieldState(key: keyof PreAuthData, val: unknown): FieldState {
  const empty = val === '' || val === null || val === undefined;
  if (!empty) return 'filled';
  if (REQUIRED.has(key)) return 'required-empty';
  return 'optional-empty';
}

function inputCls(state: FieldState) {
  const base = 'w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 transition-colors bg-white dark:bg-slate-800';
  if (state === 'filled') return base + ' border-emerald-400 dark:border-emerald-600 focus:ring-emerald-500';
  if (state === 'required-empty') return base + ' border-red-400 dark:border-red-600 focus:ring-red-400 bg-red-50 dark:bg-red-900/10';
  return base + ' border-slate-200 dark:border-slate-600 focus:ring-emerald-500';
}

// ---------------------------------------------------------------------------
// Field components
// ---------------------------------------------------------------------------
function Field({ label, name, form, onChange, type = 'text', area = false, placeholder = '', span2 = false }: {
  label: string; name: keyof PreAuthData; form: PreAuthData;
  onChange: (k: keyof PreAuthData, v: unknown) => void;
  type?: string; area?: boolean; placeholder?: string; span2?: boolean;
}) {
  const val = form[name] as string | number | undefined;
  const state = getFieldState(name, val);
  const cls = inputCls(state) + (span2 ? ' col-span-2' : '');
  return (
    <div className={span2 ? 'col-span-2' : ''}>
      <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
        {label}{REQUIRED.has(name) && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {area ? (
        <textarea rows={3} value={val ?? ''} placeholder={placeholder}
          onChange={e => onChange(name, e.target.value)}
          className={inputCls(state) + ' resize-none'} />
      ) : (
        <input type={type} value={val ?? ''} placeholder={placeholder}
          onChange={e => onChange(name, type === 'number' ? (e.target.value ? Number(e.target.value) : '') : e.target.value)}
          className={inputCls(state)} />
      )}
      {state === 'required-empty' && <p className="text-xs text-red-500 mt-0.5">Required</p>}
    </div>
  );
}

function BoolField({ label, name, form, onChange }: {
  label: string; name: keyof PreAuthData; form: PreAuthData;
  onChange: (k: keyof PreAuthData, v: unknown) => void;
}) {
  const val = form[name] as boolean | undefined;
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div onClick={() => onChange(name, !val)}
        className={'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors cursor-pointer ' +
          (val ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300 dark:border-slate-600')}>
        {val && <CheckCircle2 size={12} className="text-white" />}
      </div>
      <span className="text-sm text-slate-700 dark:text-slate-300">{label}</span>
    </label>
  );
}

function RadioGroup({ label, name, options, form, onChange }: {
  label: string; name: string; options: string[];
  form: Record<string, unknown>; onChange: (k: string, v: unknown) => void;
}) {
  const val = form[name];
  return (
    <div>
      {label && (
        <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">
          {label}
          {REQUIRED.has(name as keyof PreAuthData) && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}
      <div className="flex flex-wrap gap-4">
        {options.map(opt => (
          <label key={opt} className="flex items-center gap-1.5 cursor-pointer select-none">
            <div onClick={() => onChange(name, val === opt ? undefined : opt)}
              className={'w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ' +
                (val === opt ? 'border-emerald-500 bg-emerald-500' : 'border-slate-300 dark:border-slate-600')}>
              {val === opt && <div className="w-1.5 h-1.5 bg-white rounded-full" />}
            </div>
            <span className="text-sm text-slate-700 dark:text-slate-300">{opt}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function Section({ title, icon: Icon, children, defaultOpen = true }: {
  title: string; icon: React.ElementType; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-4 bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
            <Icon size={16} className="text-emerald-600 dark:text-emerald-400" />
          </div>
          <span className="font-semibold text-slate-900 dark:text-white text-sm">{title}</span>
        </div>
        {open ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>
      {open && <div className="px-6 py-5 space-y-4">{children}</div>}
    </div>
  );
}

function G2({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{children}</div>;
}
function G3({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">{children}</div>;
}
function G4({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">{children}</div>;
}

// ---------------------------------------------------------------------------
// Main form
// ---------------------------------------------------------------------------
export default function PreAuthForm() {
  const navigate = useNavigate();
  const [form, setForm] = useState<PreAuthData>({
    treatment_medical_management: false, treatment_surgical: false,
    treatment_intensive_care: false, treatment_investigation: false, treatment_non_allopathic: false,
    diabetes: false, hypertension: false, heart_disease: false,
    hyperlipidemias: false, osteoarthritis: false, asthma_copd: false,
    cancer: false, alcohol_drug_abuse: false, hiv_std: false,
  });
  const [preAuthId, setPreAuthId] = useState<string | null>(null);
  const [billNo, setBillNo] = useState<string | null>(null);
  const [abhaInput, setAbhaInput] = useState('');
  const [abhaLoading, setAbhaLoading] = useState(false);
  const [abhaError, setAbhaError] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [estimatingCosts, setEstimatingCosts] = useState(false);
  const [costMsg, setCostMsg] = useState<string | null>(null);
  const [nextLoading, setNextLoading] = useState(false);

  const set = useCallback((k: keyof PreAuthData | string, v: unknown) => {
    setForm(f => ({ ...f, [k]: v }));
  }, []);

  const missingCount = [...REQUIRED].filter(k => {
    const v = form[k];
    return v === '' || v === null || v === undefined;
  }).length;

  // ABHA lookup
  const handleAbhaLookup = async () => {
    const id = abhaInput.trim();
    if (!id) return;
    setAbhaLoading(true); setAbhaError(null);
    try {
      const p: AbhaPatient = await lookupAbha(id);
      setForm(f => ({
        ...f,
        abha_id: p.abha_id,
        patient_name: p.name ?? f.patient_name,
        date_of_birth: p.date_of_birth ?? f.date_of_birth,
        gender: p.gender ?? f.gender,
        age: p.age ?? f.age,
        contact: p.contact ?? f.contact,
        patient_address: p.address ?? f.patient_address,
        policy_no: p.policy_no ?? f.policy_no,
        insured_card_id: p.insured_card_id ?? f.insured_card_id,
        employee_id: p.employee_id ?? f.employee_id,
        diabetes: p.diabetes,
        hypertension: p.hypertension,
        heart_disease: p.heart_disease,
        other_conditions: p.other_conditions ?? f.other_conditions,
      }));
    } catch (e: any) {
      setAbhaError(e.response?.data?.detail || 'ABHA ID not found');
    } finally { setAbhaLoading(false); }
  };

  // Auto-calculate costs from ICD-10 / diagnosis
  const handleEstimateCosts = async () => {
    const icd10 = (form.icd10_diagnosis_code as string) || '';
    const diagnosis = (form.provisional_diagnosis as string) || '';
    if (!icd10 && !diagnosis) {
      setCostMsg('Enter ICD-10 code or provisional diagnosis first');
      setTimeout(() => setCostMsg(null), 3000);
      return;
    }
    setEstimatingCosts(true); setCostMsg(null);
    try {
      const costs = await estimateCosts(icd10, diagnosis);
      setForm(f => ({
        ...f,
        room_rent_per_day:               costs.room_rent_per_day              ?? f.room_rent_per_day,
        icu_charges_per_day:             costs.icu_charges_per_day            ?? f.icu_charges_per_day,
        ot_charges:                      costs.ot_charges                     ?? f.ot_charges,
        professional_fees:               costs.professional_fees              ?? f.professional_fees,
        medicines_consumables:           costs.medicines_consumables          ?? f.medicines_consumables,
        investigation_diagnostics_cost:  costs.investigation_diagnostics_cost ?? f.investigation_diagnostics_cost,
        other_hospital_expenses:         costs.other_hospital_expenses        ?? f.other_hospital_expenses,
        total_estimated_cost:            costs.total_estimated_cost           ?? f.total_estimated_cost,
        expected_days_in_hospital:       costs.expected_days_in_hospital      ?? f.expected_days_in_hospital,
        days_in_icu:                     costs.days_in_icu                    ?? f.days_in_icu,
        room_type:                       costs.room_type                      ?? f.room_type,
        surgery_name:                    costs.surgery_name                   ?? f.surgery_name,
        icd10_pcs_code:                  costs.icd10_pcs_code                 ?? f.icd10_pcs_code,
      }));
      setCostMsg(`Costs estimated from: ${costs.matched_diagnosis} (${costs.matched_icd10})`);
      setTimeout(() => setCostMsg(null), 5000);
    } catch (e: any) {
      setCostMsg(e.response?.data?.detail || 'No match found — fill manually');
      setTimeout(() => setCostMsg(null), 4000);
    } finally { setEstimatingCosts(false); }
  };

  // Medical extraction
  const handleExtract = async (file: File) => {
    let id = preAuthId;
    if (!id) {
      try { const r = await createPreAuth({ ...form }); id = r.id; setPreAuthId(id); } catch { return; }
    }
    setExtracting(true);
    try {
      const ext = await extractMedicalFromPdf(id!, file);
      // Helper: only overwrite a form field if the extracted value is non-null/non-empty
      const pick = <T,>(extracted: T | null | undefined, current: T): T =>
        (extracted !== null && extracted !== undefined) ? extracted : current;
      setForm(f => ({
        ...f,
        // Hospital
        hospital_name:                 pick(ext.hospital_name,                 f.hospital_name),
        hospital_location:             pick(ext.hospital_location,             f.hospital_location),
        hospital_email:                pick(ext.hospital_email,                f.hospital_email),
        hospital_id:                   pick(ext.hospital_id,                   f.hospital_id),
        rohini_id:                     pick(ext.rohini_id,                     f.rohini_id),
        // Doctor
        doctor_name:                   pick(ext.doctor_name,                   f.doctor_name),
        doctor_contact:                pick(ext.doctor_contact,                f.doctor_contact),
        doctor_qualification:          pick(ext.doctor_qualification,          f.doctor_qualification),
        doctor_registration_no:        pick(ext.doctor_registration_no,        f.doctor_registration_no),
        // Medical
        presenting_complaints:         pick(ext.presenting_complaints,         f.presenting_complaints),
        duration_of_illness:           pick(ext.duration_of_illness,           f.duration_of_illness),
        date_of_first_consultation:    pick(ext.date_of_first_consultation,    f.date_of_first_consultation),
        provisional_diagnosis:         pick(ext.provisional_diagnosis,         f.provisional_diagnosis),
        icd10_diagnosis_code:          pick(ext.icd10_diagnosis_code,          f.icd10_diagnosis_code),
        clinical_findings:             pick(ext.clinical_findings,             f.clinical_findings),
        past_history:                  pick(ext.past_history,                  f.past_history),
        // Treatment
        line_of_treatment:             pick(ext.line_of_treatment,             f.line_of_treatment),
        treatment_medical_management:  ext.treatment_medical_management  ?? f.treatment_medical_management,
        treatment_surgical:            ext.treatment_surgical            ?? (ext.surgery_name ? true : f.treatment_surgical),
        treatment_intensive_care:      ext.treatment_intensive_care      ?? f.treatment_intensive_care,
        treatment_investigation:       ext.treatment_investigation       ?? f.treatment_investigation,
        medical_management_details:    pick(ext.medical_management_details,    f.medical_management_details),
        route_of_drug_administration:  pick(ext.route_of_drug_administration,  f.route_of_drug_administration),
        surgery_name:                  pick(ext.surgery_name,                  f.surgery_name),
        icd10_pcs_code:                pick(ext.icd10_pcs_code,                f.icd10_pcs_code),
        // Admission
        admission_date:                pick(ext.admission_date,                f.admission_date),
        admission_time:                pick(ext.admission_time,                f.admission_time),
        admission_type:                pick(ext.admission_type,                f.admission_type),
        expected_days_in_hospital:     pick(ext.expected_days_in_hospital,     f.expected_days_in_hospital),
        days_in_icu:                   pick(ext.days_in_icu,                   f.days_in_icu),
        room_type:                     pick(ext.room_type,                     f.room_type),
        // Costs (only if explicitly in the document)
        room_rent_per_day:             pick(ext.room_rent_per_day,             f.room_rent_per_day),
        icu_charges_per_day:           pick(ext.icu_charges_per_day,           f.icu_charges_per_day),
        ot_charges:                    pick(ext.ot_charges,                    f.ot_charges),
        professional_fees:             pick(ext.professional_fees,             f.professional_fees),
        medicines_consumables:         pick(ext.medicines_consumables,         f.medicines_consumables),
        investigation_diagnostics_cost:pick(ext.investigation_diagnostics_cost,f.investigation_diagnostics_cost),
        other_hospital_expenses:       pick(ext.other_hospital_expenses,       f.other_hospital_expenses),
        total_estimated_cost:          pick(ext.total_estimated_cost,          f.total_estimated_cost),
        // Past medical history
        diabetes:                      ext.diabetes          ?? f.diabetes,
        diabetes_since:                pick(ext.diabetes_since,                f.diabetes_since),
        hypertension:                  ext.hypertension       ?? f.hypertension,
        hypertension_since:            pick(ext.hypertension_since,            f.hypertension_since),
        heart_disease:                 ext.heart_disease      ?? f.heart_disease,
        heart_disease_since:           pick(ext.heart_disease_since,           f.heart_disease_since),
        hyperlipidemias:               ext.hyperlipidemias    ?? f.hyperlipidemias,
        osteoarthritis:                ext.osteoarthritis     ?? f.osteoarthritis,
        asthma_copd:                   ext.asthma_copd        ?? f.asthma_copd,
        cancer:                        ext.cancer             ?? f.cancer,
        alcohol_drug_abuse:            ext.alcohol_drug_abuse ?? f.alcohol_drug_abuse,
        hiv_std:                       ext.hiv_std            ?? f.hiv_std,
        other_conditions:              pick(ext.other_conditions,              f.other_conditions),
        // Injury / RTA
        is_rta:                        ext.is_rta             ?? f.is_rta,
        date_of_injury:                pick(ext.date_of_injury,                f.date_of_injury),
        reported_to_police:            ext.reported_to_police ?? f.reported_to_police,
        fir_no:                        pick(ext.fir_no,                        f.fir_no),
        substance_abuse:               ext.substance_abuse    ?? f.substance_abuse,
        // Maternity
        maternity_g:                   pick(ext.maternity_g,                   f.maternity_g),
        maternity_p:                   pick(ext.maternity_p,                   f.maternity_p),
        maternity_l:                   pick(ext.maternity_l,                   f.maternity_l),
        maternity_a:                   pick(ext.maternity_a,                   f.maternity_a),
        expected_delivery_date:        pick(ext.expected_delivery_date,        f.expected_delivery_date),
      }));
    } finally { setExtracting(false); }
  };

  const handleSave = async () => {
    setSaving(true); setSaveMsg(null);
    try {
      if (preAuthId) {
        await updatePreAuth(preAuthId, form);
      } else {
        const r = await createPreAuth(form);
        setPreAuthId(r.id); setBillNo(r.bill_no ?? null);
      }
      setSaveMsg('Saved successfully');
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (e: any) {
      setSaveMsg('Save failed: ' + (e.response?.data?.detail || e.message));
    } finally { setSaving(false); }
  };

  const handleGeneratePdf = async () => {
    if (!preAuthId) return;
    setGenerating(true);
    try {
      await updatePreAuth(preAuthId, form);
      const blob = await generatePreAuthPdf(preAuthId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `medi_assist_pre_auth_${preAuthId.slice(0, 8)}.pdf`;
      a.click(); URL.revokeObjectURL(url);
    } finally { setGenerating(false); }
  };

  // "Next" — creates the pre-auth (generating bill_no) then navigates to the case page
  const handleNext = async () => {
    setNextLoading(true);
    try {
      let id = preAuthId;
      let bill = billNo;
      if (!id) {
        const r = await createPreAuth(form);
        id = r.id; bill = r.bill_no ?? null;
        setPreAuthId(id); setBillNo(bill);
      } else {
        await updatePreAuth(id, form);
      }
      if (bill) navigate(`/cases/${encodeURIComponent(bill)}`);
    } catch (e: any) {
      setSaveMsg('Failed: ' + (e.response?.data?.detail || e.message));
      setTimeout(() => setSaveMsg(null), 4000);
    } finally { setNextLoading(false); }
  };

  const boolToRadio = (val: boolean | undefined) =>
    val === true ? 'Yes' : val === false ? 'No' : undefined;

  return (
    <div className="space-y-6 pb-32">
      {/* ── Case header — mirrors CasePage dark card ── */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl px-7 py-6 shadow-lg">
        <div className="flex items-center gap-2 mb-3">
          <FileText size={15} className="text-emerald-400" />
          {billNo ? (
            <>
              <Link
                to={`/cases/${encodeURIComponent(billNo)}`}
                className="font-mono text-sm font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full border border-slate-700 hover:border-emerald-600 hover:text-emerald-400 transition-colors"
              >
                {billNo}
              </Link>
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-700 text-slate-300 font-semibold">
                draft
              </span>
            </>
          ) : (
            <span className="font-mono text-sm bg-slate-800 text-slate-500 px-3 py-1 rounded-full border border-slate-700">
              New Pre-Auth
            </span>
          )}
        </div>
        <h1 className="text-2xl font-extrabold text-white mb-0.5">
          {(form.patient_name as string) || 'New Pre-Authorization Request'}
        </h1>
        <p className="text-slate-400 text-sm">
          Medi Assist Insurance TPA Pvt Ltd · Part C (Revised) · Cashless Hospitalisation
          {(form.hospital_name as string) && (
            <span className="ml-2 text-slate-500">· {form.hospital_name as string}</span>
          )}
        </p>
      </div>

      {/* ABHA Lookup */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <Search size={15} className="text-emerald-500" /> Lookup by ABHA ID (auto-fills patient details)
        </p>
        <div className="flex gap-3">
          <input value={abhaInput} onChange={e => setAbhaInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAbhaLookup()}
            placeholder="e.g. 12-3456-7890-1234"
            className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
          <button onClick={handleAbhaLookup} disabled={abhaLoading || !abhaInput.trim()}
            className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold disabled:opacity-50 transition-colors flex items-center gap-2">
            {abhaLoading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Search size={14} />}
            Fetch
          </button>
        </div>
        {abhaError && <p className="mt-2 text-xs text-red-500">{abhaError}</p>}
        <div className="mt-3 flex flex-wrap gap-2">
          {['12-3456-7890-1234','14-2345-6789-0011','18-9876-5432-1001','21-1111-2222-3333','31-4444-5555-6666'].map(id => (
            <button key={id} onClick={() => setAbhaInput(id)}
              className="text-xs px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors font-mono">
              {id}
            </button>
          ))}
        </div>
      </div>

      {/* Medical Report Upload */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-5">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <Upload size={15} className="text-emerald-500" /> Upload Medical Report (auto-fills clinical fields via Gemini)
        </p>
        <label className="flex items-center gap-3 px-4 py-3 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 hover:border-emerald-400 transition-colors cursor-pointer">
          <Upload size={16} className="text-slate-400" />
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {extracting ? 'Extracting clinical data...' : 'Click to upload PDF medical report'}
          </span>
          <input type="file" accept=".pdf" className="hidden" disabled={extracting}
            onChange={e => e.target.files?.[0] && handleExtract(e.target.files[0])} />
        </label>
      </div>

      {/* ── Hospital Details ────────────────────────────────────────── */}
      <Section title="Hospital Details" icon={Building2}>
        <G2>
          <Field label="Name of the Hospital" name="hospital_name" form={form} onChange={set} />
          <Field label="Hospital Location" name="hospital_location" form={form} onChange={set} />
          <Field label="Hospital Email ID" name="hospital_email" form={form} onChange={set} />
          <Field label="Hospital ID" name="hospital_id" form={form} onChange={set} />
          <Field label="ROHINI ID" name="rohini_id" form={form} onChange={set} />
        </G2>
      </Section>

      {/* TPA (read-only) */}
      <div className="bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-slate-200 dark:border-slate-700 px-6 py-4">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Details of Third Party Administrator</p>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div><span className="text-slate-400">TPA: </span><span className="font-medium text-slate-800 dark:text-slate-200">Medi Assist Insurance TPA Pvt Ltd</span></div>
          <div><span className="text-slate-400">Phone: </span><span className="font-medium text-slate-800 dark:text-slate-200">080 22068666</span></div>
          <div><span className="text-slate-400">Toll Free Fax: </span><span className="font-medium text-slate-800 dark:text-slate-200">1800 425 9559</span></div>
        </div>
      </div>

      {/* ── Patient Details ─────────────────────────────────────────── */}
      <Section title="Patient / Insured Details  (To be filled by Insured / Patient)" icon={User}>
        <G2>
          <Field label="a) Name of the Patient" name="patient_name" form={form} onChange={set} />
          <RadioGroup label="b) Gender" name="gender" options={['Male', 'Female', 'Third gender']}
            form={form as Record<string,unknown>} onChange={set} />
          <Field label="c) Contact No." name="contact" form={form} onChange={set} />
          <Field label="d) Alternate Contact No." name="alternate_contact" form={form} onChange={set} />
          <Field label="e) Age (Years)" name="age" form={form} onChange={set} type="number" />
          <Field label="e) Age (Months)" name="age_months" form={form} onChange={set} type="number" />
          <Field label="f) Date of Birth" name="date_of_birth" form={form} onChange={set} placeholder="DD-MMM-YYYY" />
          <Field label="g) Insurer ID Card No." name="insured_card_id" form={form} onChange={set} />
          <Field label="h) Policy No. / Name of Corporate" name="policy_no" form={form} onChange={set} />
          <Field label="i) Employee ID" name="employee_id" form={form} onChange={set} />
        </G2>

        <div>
          <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
            j) Currently other medical claim / health insurance?
          </label>
          <RadioGroup label="" name="other_insurance_radio" options={['Yes', 'No']}
            form={{ other_insurance_radio: form.other_insurance === true ? 'Yes' : form.other_insurance === false ? 'No' : undefined }}
            onChange={(_, v) => set('other_insurance', v === 'Yes' ? true : v === 'No' ? false : undefined)} />
        </div>
        {form.other_insurance === true && (
          <G2>
            <Field label="j.1) Insurer Name" name="other_insurance_insurer" form={form} onChange={set} />
            <Field label="j.2) Give Details" name="other_insurance_details" form={form} onChange={set} />
          </G2>
        )}
        <G2>
          <Field label="k) Family Physician Name" name="family_physician_name" form={form} onChange={set} />
          <Field label="k.1) Family Physician Contact" name="family_physician_contact" form={form} onChange={set} />
        </G2>
        <Field label="L) Occupation of Insured Patient" name="occupation" form={form} onChange={set} />
        <Field label="m) Address of Insured Patient" name="patient_address" form={form} onChange={set} area />
      </Section>

      {/* ── Doctor / Hospital ───────────────────────────────────────── */}
      <Section title="To be Filled by the Treating Doctor / Hospital" icon={Stethoscope}>
        <G2>
          <Field label="a) Name of Treating Doctor" name="doctor_name" form={form} onChange={set} />
          <Field label="b) Contact No." name="doctor_contact" form={form} onChange={set} />
        </G2>
        <G2>
          <Field label="c) Illness / Disease with Presenting Complaints" name="presenting_complaints" form={form} onChange={set} area />
          <Field label="d) Relevant Clinical Findings" name="clinical_findings" form={form} onChange={set} area />
        </G2>
        <G2>
          <Field label="e) Duration of Present Ailment" name="duration_of_illness" form={form} onChange={set} placeholder="e.g. 18 hours" />
          <Field label="e.1) Date of First Consultation" name="date_of_first_consultation" form={form} onChange={set} placeholder="DD-MMM-YYYY" />
        </G2>
        <Field label="e.2) Past History of Present Ailment" name="past_history" form={form} onChange={set} area />
        <G2>
          <Field label="f) Provisional Diagnosis" name="provisional_diagnosis" form={form} onChange={set} />
          <Field label="f.1) ICD-10 Code" name="icd10_diagnosis_code" form={form} onChange={set} placeholder="e.g. K37" />
        </G2>

        <div>
          <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
            g) Proposed Line of Treatment
          </label>
          <div className="flex flex-wrap gap-5">
            <BoolField label="Medical Management"    name="treatment_medical_management" form={form} onChange={set} />
            <BoolField label="Surgical Management"   name="treatment_surgical"            form={form} onChange={set} />
            <BoolField label="Intensive Care"        name="treatment_intensive_care"      form={form} onChange={set} />
            <BoolField label="Investigation"         name="treatment_investigation"       form={form} onChange={set} />
            <BoolField label="Non-Allopathic"        name="treatment_non_allopathic"      form={form} onChange={set} />
          </div>
        </div>

        <G2>
          <div className="space-y-3">
            <Field label="h) Medical Management / Investigation Details" name="medical_management_details" form={form} onChange={set} area />
            <RadioGroup label="h.1) Route of Drug Administration" name="route_of_drug_administration"
              options={['IV', 'Oral', 'Other']} form={form as Record<string,unknown>} onChange={set} />
          </div>
          <div className="space-y-4">
            <Field label="i) If Surgical — Name of Surgery" name="surgery_name" form={form} onChange={set} />
            <Field label="i.1) ICD-10 PCS Code" name="icd10_pcs_code" form={form} onChange={set} placeholder="e.g. 0DTJ4ZZ" />
          </div>
        </G2>

        <G2>
          <Field label="j) Other Treatment Details" name="other_treatment_details" form={form} onChange={set} area />
          <Field label="k) How Did Injury Occur" name="injury_details" form={form} onChange={set} area />
        </G2>

        {/* Accident */}
        <div className="bg-slate-50 dark:bg-slate-800/40 rounded-xl p-4 space-y-3 border border-slate-200 dark:border-slate-700">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">L) In Case of Accident</p>
          <G2>
            <RadioGroup label="i. Is it RTA?" name="is_rta_radio" options={['Yes', 'No']}
              form={{ is_rta_radio: boolToRadio(form.is_rta) }}
              onChange={(_, v) => set('is_rta', v === 'Yes' ? true : v === 'No' ? false : undefined)} />
            <RadioGroup label="iii. Reported to Police?" name="rtp_radio" options={['Yes', 'No']}
              form={{ rtp_radio: boolToRadio(form.reported_to_police) }}
              onChange={(_, v) => set('reported_to_police', v === 'Yes' ? true : v === 'No' ? false : undefined)} />
            <Field label="ii. Date of Injury" name="date_of_injury" form={form} onChange={set} placeholder="DD-MMM-YYYY" />
            <Field label="iv. FIR No." name="fir_no" form={form} onChange={set} />
          </G2>
          <G2>
            <RadioGroup label="v. Injury/Disease due to Substance Abuse / Alcohol?" name="sa_radio" options={['Yes', 'No']}
              form={{ sa_radio: boolToRadio(form.substance_abuse) }}
              onChange={(_, v) => set('substance_abuse', v === 'Yes' ? true : v === 'No' ? false : undefined)} />
            <RadioGroup label="vi. Test Conducted to Establish This?" name="sat_radio" options={['Yes', 'No']}
              form={{ sat_radio: boolToRadio(form.substance_abuse_test_done) }}
              onChange={(_, v) => set('substance_abuse_test_done', v === 'Yes' ? true : v === 'No' ? false : undefined)} />
          </G2>
        </div>

        {/* Maternity */}
        <div className="bg-slate-50 dark:bg-slate-800/40 rounded-xl p-4 space-y-3 border border-slate-200 dark:border-slate-700">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">m) In Case of Maternity</p>
          <G4>
            <Field label="G (Gravida)" name="maternity_g" form={form} onChange={set} />
            <Field label="P (Para)"    name="maternity_p" form={form} onChange={set} />
            <Field label="L (Living)"  name="maternity_l" form={form} onChange={set} />
            <Field label="A (Abortion)" name="maternity_a" form={form} onChange={set} />
          </G4>
          <Field label="n) Expected Date of Delivery" name="expected_delivery_date" form={form} onChange={set} placeholder="DD-MMM-YYYY" />
        </div>
      </Section>

      {/* ── Admission Details ───────────────────────────────────────── */}
      <Section title="Details of the Patient Admitted" icon={Calendar}>
        <G2>
          <Field label="a) Date of Admission" name="admission_date" form={form} onChange={set} placeholder="DD-MMM-YYYY" />
          <Field label="b) Time of Admission" name="admission_time" form={form} onChange={set} placeholder="HH:MM" />
        </G2>
        <RadioGroup label="c) This is an Emergency / Planned Hospitalisation Event"
          name="admission_type" options={['Emergency', 'Planned']}
          form={form as Record<string,unknown>} onChange={set} />
        <G3>
          <Field label="d) Expected No. of Days Stay in Hospital" name="expected_days_in_hospital" form={form} onChange={set} type="number" />
          <Field label="e) Days in ICU" name="days_in_icu" form={form} onChange={set} type="number" />
          <Field label="f) Room Type" name="room_type" form={form} onChange={set} placeholder="General / Private / ICU" />
        </G3>
      </Section>

      {/* ── Estimated Costs ─────────────────────────────────────────── */}
      <Section title="Estimated Cost of Hospitalization (INR)" icon={IndianRupee}>
        {/* Auto-calculate button */}
        <div className="flex items-center gap-3 flex-wrap mb-1">
          <button
            onClick={handleEstimateCosts}
            disabled={estimatingCosts}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold rounded-xl transition-colors disabled:opacity-60"
          >
            {estimatingCosts
              ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              : <Sparkles size={13} />}
            {estimatingCosts ? 'Calculating…' : 'Auto-Calculate from Diagnosis'}
          </button>
          {costMsg && (
            <span className={`text-xs font-medium ${costMsg.startsWith('Costs estimated') ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
              {costMsg}
            </span>
          )}
        </div>
        <G2>
          <Field label="g) Per Day Room Rent + Nursing + Patient Diet" name="room_rent_per_day" form={form} onChange={set} type="number" placeholder="Rs." />
          <Field label="h) Expected Cost for Investigation + Diagnostics" name="investigation_diagnostics_cost" form={form} onChange={set} type="number" placeholder="Rs." />
          <Field label="i) ICU Charges (per day)" name="icu_charges_per_day" form={form} onChange={set} type="number" placeholder="Rs." />
          <Field label="j) OT Charges" name="ot_charges" form={form} onChange={set} type="number" placeholder="Rs." />
          <Field label="k) Professional Fees (Surgeon + Anaesthetist + Consultation)" name="professional_fees" form={form} onChange={set} type="number" placeholder="Rs." />
          <Field label="L) Medicines + Consumables + Cost of Implants" name="medicines_consumables" form={form} onChange={set} type="number" placeholder="Rs." />
          <Field label="m) Other Hospital Expenses if Any" name="other_hospital_expenses" form={form} onChange={set} type="number" placeholder="Rs." />
          <Field label="n) All Inclusive Package Charges if Any" name="package_charges" form={form} onChange={set} type="number" placeholder="Rs." />
        </G2>
        <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-4 border border-emerald-200 dark:border-emerald-800">
          <Field label="o) Sum Total Expected Cost of Hospitalization" name="total_estimated_cost" form={form} onChange={set} type="number" placeholder="Rs." />
        </div>
      </Section>

      {/* ── Past Medical History ────────────────────────────────────── */}
      <Section title="p. Mandatory Past History of Chronic Illness (If Yes, Since Month/Year)" icon={Shield}>
        <p className="text-xs text-slate-500 dark:text-slate-400 -mt-1">Check the condition and fill the month/year when it was first diagnosed.</p>
        <div className="space-y-3">
          {([
            ['diabetes',           'Diabetes',                    'diabetes_since'],
            ['heart_disease',      'Heart Disease',               'heart_disease_since'],
            ['hypertension',       'Hypertension',                'hypertension_since'],
            ['hyperlipidemias',    'Hyperlipidemias',             'hyperlipidemias_since'],
            ['osteoarthritis',     'Osteoarthritis',              'osteoarthritis_since'],
            ['asthma_copd',        'Asthma / COPD / Bronchitis',  'asthma_copd_since'],
            ['cancer',             'Cancer',                      'cancer_since'],
            ['alcohol_drug_abuse', 'Alcohol or Drug Abuse',       'alcohol_drug_abuse_since'],
            ['hiv_std',            'Any HIV or STD / Related Ailments', 'hiv_std_since'],
          ] as [keyof PreAuthData, string, keyof PreAuthData][]).map(([key, label, sinceKey]) => (
            <div key={key} className="flex items-center gap-4 flex-wrap">
              <div className="w-56">
                <BoolField label={label} name={key} form={form} onChange={set} />
              </div>
              {form[key] && (
                <div className="flex-1 min-w-32 max-w-48">
                  <Field label="Since (MM/YYYY)" name={sinceKey} form={form} onChange={set} placeholder="e.g. 03/2015" />
                </div>
              )}
            </div>
          ))}
          <Field label="10. Any Other Ailment — Give Details" name="other_conditions" form={form} onChange={set} area />
        </div>
      </Section>

      {/* ── Declaration ─────────────────────────────────────────────── */}
      <Section title="Declaration" icon={FileText} defaultOpen={false}>
        <G3>
          <Field label="a) Doctor Name" name="doctor_name" form={form} onChange={set} />
          <Field label="b) Qualification" name="doctor_qualification" form={form} onChange={set} placeholder="e.g. MS, MBBS" />
          <Field label="c) Registration No. with State Code" name="doctor_registration_no" form={form} onChange={set} />
        </G3>
        <G2>
          <Field label="Patient / Insured Name" name="patient_name" form={form} onChange={set} />
          <Field label="Patient Email ID (Optional)" name="patient_email" form={form} onChange={set} type="email" />
        </G2>
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          I hereby declare to abide by the terms and conditions of the policy. I agree to allow the hospital
          to submit all original documents pertaining to hospitalization to the Insurer/TPA after discharge.
          I agree to sign on the Final Bill and the Discharge Summary before my discharge.
          All non-medical expenses and amounts over and above the limit authorized by the Insurer/TPA will be paid by me.
        </div>
      </Section>

      {/* Missing fields banner */}
      {missingCount > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-2xl px-5 py-4 flex items-start gap-3">
          <AlertCircle size={18} className="text-amber-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-800 dark:text-amber-400">
              {missingCount} required field{missingCount > 1 ? 's' : ''} missing
            </p>
            <p className="text-xs text-amber-700 dark:text-amber-500 mt-0.5">
              {[...REQUIRED]
                .filter(k => { const v = form[k]; return v === '' || v === null || v === undefined; })
                .map(k => FIELD_LABELS[k] || k)
                .join(', ')}
            </p>
          </div>
        </div>
      )}

      {/* Sticky action bar */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-t border-slate-200 dark:border-slate-700 px-8 py-4 flex items-center justify-between gap-4">
        <div className="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-3">
          {billNo && (
            <span className="font-mono text-xs text-slate-400 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-lg">
              {billNo}
            </span>
          )}
          {saveMsg
            ? <span className={saveMsg.startsWith('Save failed') ? 'text-red-500' : 'text-emerald-500'}>{saveMsg}</span>
            : <span>{missingCount > 0 ? `${missingCount} required field${missingCount > 1 ? 's' : ''} pending` : 'All required fields filled'}</span>}
        </div>
        <div className="flex gap-3">
          <button onClick={handleSave} disabled={saving}
            className="px-5 py-2 rounded-xl border border-emerald-600 text-emerald-600 dark:text-emerald-400 text-sm font-semibold hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors disabled:opacity-50 flex items-center gap-2">
            {saving ? <span className="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-500 rounded-full animate-spin" /> : <ClipboardList size={14} />}
            Save Draft
          </button>
          <button onClick={handleGeneratePdf} disabled={generating || !preAuthId}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2">
            {generating ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Download size={14} />}
            Generate &amp; Download PDF
          </button>
          <button onClick={handleNext} disabled={nextLoading || !form.abha_id}
            title={!form.abha_id ? 'Enter ABHA ID first' : ''}
            className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
            {nextLoading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
            Next: Enhancement
          </button>
        </div>
      </div>
    </div>
  );
}

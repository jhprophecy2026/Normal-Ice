import axios from 'axios';
import type {
  ProcessResponse,
  HealthResponse,
  PatientSummary,
  StoredPatientRecord,
  FlagsResponse,
  AbhaPatient,
  PreAuthData,
  PreAuthResponse,
  MedicalExtract,
  EnhancementData,
  EnhancementResponse,
  PatientCaseHistory,
  DischargeData,
  DischargeResponse,
  DischargeExtract,
  SettlementData,
  SettlementResponse,
  CaseSummary,
  CaseDetail,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export type { ProcessResponse, HealthResponse };

// ---------------------------------------------------------------------------
// Existing endpoints
// ---------------------------------------------------------------------------
export const healthCheck = async (): Promise<HealthResponse> => {
  const response = await api.get<HealthResponse>('/health');
  return response.data;
};

export const processPdf = async (file: File): Promise<ProcessResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<ProcessResponse>('/process-pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

// ---------------------------------------------------------------------------
// Patient endpoints
// ---------------------------------------------------------------------------
export const getPatients = async (search?: string): Promise<PatientSummary[]> => {
  const params = search ? { search } : {};
  const response = await api.get<{ success: boolean; patients: PatientSummary[] }>('/patients', { params });
  return response.data.patients;
};

export const getPatient = async (patientId: string): Promise<StoredPatientRecord> => {
  const response = await api.get<{ success: boolean; patient: StoredPatientRecord }>(`/patients/${patientId}`);
  return response.data.patient;
};

export const getPatientFlags = async (patientId: string): Promise<FlagsResponse> => {
  const response = await api.get<FlagsResponse>(`/patients/${patientId}/flags`);
  return response.data;
};

export const getPatientBundles = async (patientId: string): Promise<any[]> => {
  const response = await api.get<{ success: boolean; bundles: any[] }>(`/patients/${patientId}/bundles`);
  return response.data.bundles;
};

export const deletePatient = async (patientId: string): Promise<void> => {
  await api.delete(`/patients/${patientId}`);
};

// ---------------------------------------------------------------------------
// Pre-Authorization endpoints
// ---------------------------------------------------------------------------
export const lookupAbha = async (abhaId: string): Promise<AbhaPatient> => {
  const response = await api.get<AbhaPatient>(`/abha/${encodeURIComponent(abhaId)}`);
  return response.data;
};

export const createPreAuth = async (data: PreAuthData): Promise<PreAuthResponse> => {
  const response = await api.post<PreAuthResponse>('/pre-auth', data);
  return response.data;
};

export const listPreAuths = async (): Promise<PreAuthResponse[]> => {
  const response = await api.get<PreAuthResponse[]>('/pre-auth');
  return response.data;
};

export const getPreAuth = async (id: string): Promise<PreAuthResponse> => {
  const response = await api.get<PreAuthResponse>(`/pre-auth/${id}`);
  return response.data;
};

export const updatePreAuth = async (id: string, data: PreAuthData): Promise<PreAuthResponse> => {
  const response = await api.put<PreAuthResponse>(`/pre-auth/${id}`, data);
  return response.data;
};

export const extractMedicalFromPdf = async (preAuthId: string, file: File): Promise<MedicalExtract> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<MedicalExtract>(
    `/pre-auth/${preAuthId}/extract-medical`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return response.data;
};

export const generatePreAuthPdf = async (id: string): Promise<Blob> => {
  const response = await api.post(`/pre-auth/${id}/generate-pdf`, {}, { responseType: 'blob' });
  return response.data;
};

export const estimateCosts = async (icd10: string, diagnosis: string): Promise<Record<string, any>> => {
  const response = await api.get('/pre-auth/estimate-costs', {
    params: { icd10, diagnosis },
  });
  return response.data;
};

export const listDummyCases = async (): Promise<{ index: number; label: string }[]> => {
  const response = await api.get('/pre-auth/dummy-cases');
  return response.data;
};

export const getDummyCase = async (index: number): Promise<{ label: string; data: Record<string, any> }> => {
  const response = await api.get(`/pre-auth/dummy-cases/${index}`);
  return response.data;
};

// ---------------------------------------------------------------------------
// Enhancement endpoints
// ---------------------------------------------------------------------------
export const getPatientCaseHistory = async (abhaId: string): Promise<PatientCaseHistory[]> => {
  const response = await api.get<PatientCaseHistory[]>(`/enhancement/patient/${encodeURIComponent(abhaId)}`);
  return response.data;
};

export const createEnhancement = async (preAuthId: string, data: EnhancementData): Promise<EnhancementResponse> => {
  const response = await api.post<EnhancementResponse>(`/enhancement/pre-auth/${preAuthId}`, data);
  return response.data;
};

export const updateEnhancement = async (id: string, data: EnhancementData): Promise<EnhancementResponse> => {
  const response = await api.put<EnhancementResponse>(`/enhancement/${id}`, data);
  return response.data;
};

export const getEnhancementsForPreAuth = async (preAuthId: string): Promise<EnhancementResponse[]> => {
  const response = await api.get<EnhancementResponse[]>(`/enhancement/pre-auth/${preAuthId}`);
  return response.data;
};

export const extractEnhancementData = async (preAuthId: string, file: File): Promise<EnhancementExtract> => {
  const form = new FormData();
  form.append('file', file);
  const response = await api.post<EnhancementExtract>(`/enhancement/pre-auth/${preAuthId}/extract-pdf`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

// ---------------------------------------------------------------------------
// Cases endpoints
// ---------------------------------------------------------------------------
export const listCases = async (): Promise<CaseSummary[]> => {
  const response = await api.get<CaseSummary[]>('/cases');
  return response.data;
};

export const getCase = async (billNo: string): Promise<CaseDetail> => {
  const response = await api.get<CaseDetail>(`/cases/${encodeURIComponent(billNo)}`);
  return response.data;
};

// ---------------------------------------------------------------------------
// Discharge endpoints
// ---------------------------------------------------------------------------
export const createDischarge = async (data: DischargeData): Promise<DischargeResponse> => {
  const response = await api.post<DischargeResponse>('/discharge', data);
  return response.data;
};

export const updateDischarge = async (id: string, data: Partial<DischargeData>): Promise<DischargeResponse> => {
  const response = await api.put<DischargeResponse>(`/discharge/${id}`, data);
  return response.data;
};

export const extractDischargeData = async (dischargeId: string, file: File): Promise<DischargeExtract> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<DischargeExtract>(`/discharge/${dischargeId}/extract`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const getDischargeByBill = async (billNo: string): Promise<DischargeResponse | null> => {
  try {
    const response = await api.get<DischargeResponse>(`/discharge/by-bill/${encodeURIComponent(billNo)}`);
    return response.data;
  } catch {
    return null;
  }
};

// ---------------------------------------------------------------------------
// Settlement endpoints
// ---------------------------------------------------------------------------
export const createSettlement = async (data: SettlementData): Promise<SettlementResponse> => {
  const response = await api.post<SettlementResponse>('/settlement', data);
  return response.data;
};

export const updateSettlement = async (id: string, data: Partial<SettlementData>): Promise<SettlementResponse> => {
  const response = await api.put<SettlementResponse>(`/settlement/${id}`, data);
  return response.data;
};

// ---------------------------------------------------------------------------
// Config endpoints
// ---------------------------------------------------------------------------
export const getCostEstimates = async (): Promise<{ _meta: any; data: any[] }> => {
  const response = await api.get('/config/cost-estimates');
  return response.data;
};

export const updateCostEstimates = async (data: any[]): Promise<{ success: boolean; count: number }> => {
  const response = await api.put('/config/cost-estimates', { data });
  return response.data;
};

export const uploadCostEstimatesFile = async (file: File): Promise<{ success: boolean; count: number }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/config/cost-estimates/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

// ---------------------------------------------------------------------------
// Financial Audit
// ---------------------------------------------------------------------------
export const getFinancialAudit = async (abhaId: string): Promise<import('../types/api').FinancialAudit> => {
  const response = await api.get(`/financial-audit/${encodeURIComponent(abhaId)}`);
  return response.data;
};

// ---------------------------------------------------------------------------
// MIS Report
// ---------------------------------------------------------------------------
export const downloadMisReport = async (period: 'weekly' | 'monthly' | 'yearly'): Promise<void> => {
  const response = await api.get('/mis/report', { params: { period }, responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement('a');
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  a.href = url;
  a.download = `MIS_Report_${period}_${date}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
};

export default api;

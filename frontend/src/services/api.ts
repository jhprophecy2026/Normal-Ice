import axios from 'axios';
import type {
  ProcessResponse,
  HealthResponse,
  PatientSummary,
  StoredPatientRecord,
  FlagsResponse,
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

export default api;

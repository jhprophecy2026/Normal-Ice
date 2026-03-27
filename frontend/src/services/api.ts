import axios from 'axios';
import type { ProcessResponse, HealthResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export type { ProcessResponse, HealthResponse };

export const healthCheck = async (): Promise<HealthResponse> => {
  const response = await api.get<HealthResponse>('/health');
  return response.data;
};

export const processPdf = async (file: File): Promise<ProcessResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<ProcessResponse>('/process-pdf', formData);
  return response.data;
};

export default api;

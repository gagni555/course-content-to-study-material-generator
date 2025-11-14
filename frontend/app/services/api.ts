import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
});

// Request interceptor to add auth token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token might be expired, clear it and redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Authentication API calls
export const authAPI = {
  register: (userData: { email: string; username?: string; full_name?: string; password: string }) => 
    api.post('/auth/register', userData),
  
  login: (credentials: { email: string; password: string }) => 
    api.post('/auth/login', credentials),
  
  getMe: () => api.get('/auth/me'),
};

// Document processing API calls
export const documentAPI = {
  uploadDocument: (file: File, metadata?: any) => {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add metadata if provided
    if (metadata) {
      Object.keys(metadata).forEach(key => {
        if (metadata[key] !== undefined && metadata[key] !== null) {
          formData.append(key, metadata[key]);
        }
      });
    }
    
    return api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  getProcessingStatus: (jobId: string) => 
    api.get(`/documents/status/${jobId}`),
  
  getDocument: (documentId: string) => 
    api.get(`/documents/${documentId}`),
  
  getStudyGuide: (documentId: string) => 
    api.get(`/documents/${documentId}/study-guide`),
  
  exportStudyGuide: (documentId: string, format: string) => 
    api.post(`/documents/${documentId}/export/${format}`),
};
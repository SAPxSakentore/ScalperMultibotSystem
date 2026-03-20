import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// Interceptor: handle offline
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      console.warn('Network error — offline mode')
    }
    return Promise.reject(error)
  }
)

export const projectsApi = {
  list: (params) => api.get('/projects', { params }),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.patch(`/projects/${id}`, data),
  getItdChecklist: (id) => api.get(`/projects/${id}/itd-checklist`),
  generatePlan: (id) => api.post(`/projects/${id}/generate-plan`),
  analyzeRisks: (id) => api.post(`/projects/${id}/analyze-risks`),
}

export const documentsApi = {
  list: (projectId, params) => api.get(`/documents/project/${projectId}`, { params }),
  generateOjr: (data) => api.post('/documents/generate/ojr', data),
  generateAosr: (data) => api.post('/documents/generate/aosr', data),
  generateHydraulicTest: (data) => api.post('/documents/generate/hydraulic-test', data),
  generateKs11: (projectId) => api.post(`/documents/generate/ks11?project_id=${projectId}`),
  download: (docId) => `/api/documents/${docId}/download`,
  checkWithAi: (docId) => api.post(`/documents/${docId}/check-with-ai`),
}

export const agentsApi = {
  list: () => api.get('/agents'),
  get: (role) => api.get(`/agents/${role}`),
  chat: (role, data) => api.post(`/agents/${role}/chat`, data),
}

export const normativesApi = {
  list: () => api.get('/normatives'),
}

export default api

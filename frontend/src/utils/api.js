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
  getProgress: (id) => api.get(`/projects/${id}/progress`),
}

export const documentsApi = {
  list: (projectId, params) => api.get(`/documents/project/${projectId}`, { params }),
  generateOjr: (data) => api.post('/documents/generate/ojr', data),
  generateAosr: (data) => api.post('/documents/generate/aosr', data),
  generateHydraulicTest: (data) => api.post('/documents/generate/hydraulic-test', data),
  generateKs11: (projectId) => api.post(`/documents/generate/ks11?project_id=${projectId}`),
  generatePpr: (data) => api.post('/documents/generate/ppr', data),
  generateTechCard: (data) => api.post('/documents/generate/tech-card', data),
  phases: () => api.get('/documents/phases'),
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

export const shiftReportsApi = {
  phases: () => api.get('/shift-reports/phases'),
  list: (projectId, params) => api.get(`/shift-reports/projects/${projectId}/`, { params }),
  get: (reportId) => api.get(`/shift-reports/${reportId}`),
  create: (data) => api.post('/shift-reports/', data),
  update: (reportId, data) => api.patch(`/shift-reports/${reportId}`, data),
  delete: (reportId) => api.delete(`/shift-reports/${reportId}`),
  finalize: (reportId, signedBy) =>
    api.post(`/shift-reports/${reportId}/finalize`, null, { params: signedBy ? { signed_by: signedBy } : {} }),
  download: (reportId) => `/api/shift-reports/${reportId}/download`,
  uploadPdf: (projectId, file, docCategory) => {
    const form = new FormData()
    form.append('file', file)
    form.append('doc_category', docCategory || 'прочее')
    return api.post(`/shift-reports/projects/${projectId}/upload-pdf`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listPdfs: (projectId) => api.get(`/shift-reports/projects/${projectId}/pdfs`),
  deletePdf: (projectId, uploadId) => api.delete(`/shift-reports/projects/${projectId}/pdfs/${uploadId}`),
}

export default api

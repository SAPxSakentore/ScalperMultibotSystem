import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { projectsApi } from '../utils/api'
import { Plus, FolderOpen, MapPin, Gauge } from 'lucide-react'

const PROJECT_TYPE_LABELS = {
  gas_pipeline_high: 'Газопровод высокого давления',
  gas_pipeline_medium: 'Газопровод среднего давления',
  gas_pipeline_low: 'Газопровод низкого давления',
  oil_pipeline: 'Нефтепровод',
  water_pipeline: 'Водопровод',
  industrial_building: 'Промышленное здание',
  road: 'Дорога',
  other: 'Прочее',
}

function CreateProjectModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    code: '',
    name: '',
    project_type: 'gas_pipeline_high',
    region: '',
    district: '',
    total_length_km: '',
    diameter_mm: '',
    working_pressure_mpa: '',
    customer_name: '',
    contractor_name: '',
    designer_name: '',
    technical_supervisor: '',
  })

  const mutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (data) => { onSuccess(data.data); onClose() },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = { ...form }
    if (payload.total_length_km) payload.total_length_km = parseFloat(payload.total_length_km)
    if (payload.diameter_mm) payload.diameter_mm = parseFloat(payload.diameter_mm)
    if (payload.working_pressure_mpa) payload.working_pressure_mpa = parseFloat(payload.working_pressure_mpa)
    mutation.mutate(payload)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-xl font-semibold">Создать новый проект</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Шифр проекта *</label>
              <input
                required
                value={form.code}
                onChange={e => setForm({...form, code: e.target.value})}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                placeholder="МГ-2024-001"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Тип объекта *</label>
              <select
                value={form.project_type}
                onChange={e => setForm({...form, project_type: e.target.value})}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              >
                {Object.entries(PROJECT_TYPE_LABELS).map(([val, label]) => (
                  <option key={val} value={val}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Наименование объекта *</label>
            <input
              required
              value={form.name}
              onChange={e => setForm({...form, name: e.target.value})}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Строительство МГ «Урал — Алматы» диаметром 1020 мм"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Область</label>
              <input
                value={form.region}
                onChange={e => setForm({...form, region: e.target.value})}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Алматинская область"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Район</label>
              <input
                value={form.district}
                onChange={e => setForm({...form, district: e.target.value})}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Карасайский район"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Длина (км)</label>
              <input
                type="number" step="0.1"
                value={form.total_length_km}
                onChange={e => setForm({...form, total_length_km: e.target.value})}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                placeholder="15.5"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Диаметр (мм)</label>
              <input
                type="number"
                value={form.diameter_mm}
                onChange={e => setForm({...form, diameter_mm: e.target.value})}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                placeholder="1020"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Давление (МПа)</label>
              <input
                type="number" step="0.1"
                value={form.working_pressure_mpa}
                onChange={e => setForm({...form, working_pressure_mpa: e.target.value})}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                placeholder="7.5"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Заказчик</label>
            <input
              value={form.customer_name}
              onChange={e => setForm({...form, customer_name: e.target.value})}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder="АО «КазТрансГаз»"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Генподрядчик</label>
            <input
              value={form.contractor_name}
              onChange={e => setForm({...form, contractor_name: e.target.value})}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder="ТОО «СтройГаз Казахстан»"
            />
          </div>

          {mutation.error && (
            <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">
              {mutation.error.response?.data?.detail || 'Ошибка создания проекта'}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? 'Создание...' : 'Создать проект'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Projects() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(r => r.data),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Проекты</h2>
          <p className="text-slate-500 mt-1">Строительные проекты Республики Казахстан</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={18} />
          Новый проект
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-slate-400">Загрузка...</div>
      ) : projects.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400">
          <FolderOpen size={48} className="mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">Нет проектов</p>
          <p className="text-sm mt-1">Создайте первый строительный проект</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {projects.map(project => (
            <a
              key={project.id}
              href={`/projects/${project.id}`}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                      {project.code}
                    </span>
                    <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                      {PROJECT_TYPE_LABELS[project.project_type] || project.project_type}
                    </span>
                  </div>
                  <h3 className="font-semibold text-slate-800">{project.name}</h3>
                  <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                    {project.region && (
                      <span className="flex items-center gap-1">
                        <MapPin size={13} /> {project.region}
                      </span>
                    )}
                    {project.total_length_km && (
                      <span>📏 {project.total_length_km} км</span>
                    )}
                    {project.diameter_mm && (
                      <span>⌀ {project.diameter_mm} мм</span>
                    )}
                    {project.working_pressure_mpa && (
                      <span className="flex items-center gap-1">
                        <Gauge size={13} /> {project.working_pressure_mpa} МПа
                      </span>
                    )}
                  </div>
                  {project.customer_name && (
                    <div className="text-xs text-slate-400 mt-1">
                      Заказчик: {project.customer_name}
                    </div>
                  )}
                </div>
              </div>
            </a>
          ))}
        </div>
      )}

      {showModal && (
        <CreateProjectModal
          onClose={() => setShowModal(false)}
          onSuccess={() => queryClient.invalidateQueries(['projects'])}
        />
      )}
    </div>
  )
}

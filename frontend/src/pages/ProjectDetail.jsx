import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef, useCallback } from 'react'
import { projectsApi, documentsApi, shiftReportsApi, workSectionsApi } from '../utils/api'
import {
  FileText, Loader2, CheckSquare, BarChart2, AlertTriangle,
  ClipboardList, Upload, Trash2, BookOpen, ChevronDown, ChevronUp,
  FileCheck, X, CheckCircle2, TrendingUp, Download, AlertOctagon,
  Plus, MapPin, Calendar, User, Check, Pencil,
} from 'lucide-react'
import TraceProgress from '../components/TraceProgress'

function ProgressBadge({ projectId }) {
  const { data } = useQuery({
    queryKey: ['progress', projectId],
    queryFn: () => projectsApi.getProgress(projectId).then(r => r.data),
    enabled: !!projectId,
  })
  if (!data) return null
  const pct = data.overall_pct
  const done = data.overall_done_km
  const activePhases = data.phases.filter(p => p.has_data).length
  return (
    <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 text-slate-600">
          <TrendingUp size={14} className="text-blue-500" />
          Прогресс строительства
        </span>
        <div className="flex items-center gap-3">
          <span className="text-slate-500">{done} км</span>
          <span className={`font-bold text-base ${pct >= 100 ? 'text-green-700' : pct >= 60 ? 'text-blue-700' : pct >= 20 ? 'text-amber-700' : 'text-orange-600'}`}>
            {pct !== null ? `${pct}%` : '—'}
          </span>
          <span className="text-xs text-slate-400">{activePhases} фаз активны</span>
        </div>
      </div>
      {pct !== null && (
        <div className="h-2.5 bg-slate-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${pct >= 100 ? 'bg-green-500' : pct >= 60 ? 'bg-blue-500' : pct >= 20 ? 'bg-amber-400' : 'bg-orange-400'}`}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}

const TAB_LABELS = ['Обзор', 'ИТД', 'Прогресс', 'Разделы работ', 'Документы', 'ПД/ППР']

const DOC_CATEGORIES = ['ПОС', 'ППР', 'ПД', 'НТД', 'Экспертиза', 'прочее']

export default function ProjectDetail() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState(0)
  const [planResult, setPlanResult] = useState(null)
  const [risksResult, setRisksResult] = useState(null)
  const [itdChecklist, setItdChecklist] = useState(null)

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id).then(r => r.data),
  })

  const { data: documents = [] } = useQuery({
    queryKey: ['documents', id],
    queryFn: () => documentsApi.list(id).then(r => r.data),
    enabled: !!id,
  })

  const planMutation = useMutation({
    mutationFn: () => projectsApi.generatePlan(id),
    onSuccess: (data) => setPlanResult(data.data),
  })

  const risksMutation = useMutation({
    mutationFn: () => projectsApi.analyzeRisks(id),
    onSuccess: (data) => setRisksResult(data.data),
  })

  const checklistMutation = useMutation({
    mutationFn: () => projectsApi.getItdChecklist(id),
    onSuccess: (data) => setItdChecklist(data.data),
  })

  const generateOjrMutation = useMutation({
    mutationFn: () => documentsApi.generateOjr({ project_id: id }),
    onSuccess: () => queryClient.invalidateQueries(['documents', id]),
  })

  const generateKs11Mutation = useMutation({
    mutationFn: () => documentsApi.generateKs11(id),
    onSuccess: () => queryClient.invalidateQueries(['documents', id]),
  })

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const deleteMutation = useMutation({
    mutationFn: () => projectsApi.delete(id),
    onSuccess: () => { window.location.href = '/projects' },
  })

  if (isLoading) return <div className="text-center py-12 text-slate-400">Загрузка...</div>
  if (!project) return <div className="text-center py-12 text-red-400">Проект не найден</div>

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">{project.code}</span>
            </div>
            <h2 className="text-xl font-bold text-slate-800">{project.name}</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
              {project.region && <div><span className="text-slate-400">Регион:</span> <span className="text-slate-700">{project.region}</span></div>}
              {project.total_length_km && <div><span className="text-slate-400">Длина:</span> <span className="text-slate-700">{project.total_length_km} км</span></div>}
              {project.diameter_mm && <div><span className="text-slate-400">Диаметр:</span> <span className="text-slate-700">{project.diameter_mm} мм</span></div>}
              {project.working_pressure_mpa && <div><span className="text-slate-400">Давление:</span> <span className="text-slate-700">{project.working_pressure_mpa} МПа</span></div>}
            </div>
            {project.customer_name && (
              <div className="text-sm text-slate-500 mt-2">Заказчик: {project.customer_name}</div>
            )}
            {project.contractor_name && (
              <div className="text-sm text-slate-500">Подрядчик: {project.contractor_name}</div>
            )}
            <ProgressBadge projectId={id} />
          </div>
          <div className="flex flex-col gap-2 shrink-0">
            <Link
              to={`/projects/${id}/shift-reports`}
              className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors"
            >
              <ClipboardList size={16} />
              Сменные рапорты
            </Link>
            <a
              href={projectsApi.exportItd(id)}
              target="_blank" rel="noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-lg text-sm font-medium hover:bg-emerald-100 transition-colors"
            >
              <Download size={16} />
              Экспорт ИТД (ZIP)
            </a>
            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors"
              >
                <Trash2 size={16} />
                Удалить проект
              </button>
            ) : (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-1.5 text-red-700 text-xs font-medium">
                  <AlertOctagon size={14} /> Удалить безвозвратно?
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => deleteMutation.mutate()}
                    disabled={deleteMutation.isPending}
                    className="flex-1 px-3 py-1.5 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                  >
                    {deleteMutation.isPending ? 'Удаляю...' : 'Да, удалить'}
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="flex-1 px-3 py-1.5 text-xs bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1 w-fit flex-wrap">
        {TAB_LABELS.map((label, i) => (
          <button
            key={i}
            onClick={() => setTab(i)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === i ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-600 hover:text-slate-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab 0: Overview */}
      {tab === 0 && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <BarChart2 size={18} className="text-blue-500" />
              План проекта
            </h3>
            {planResult ? (
              <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto scrollbar-thin">
                {planResult.plan}
              </div>
            ) : (
              <button
                onClick={() => planMutation.mutate()}
                disabled={planMutation.isPending}
                className="w-full border border-blue-300 text-blue-600 rounded-lg py-2 text-sm hover:bg-blue-50 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {planMutation.isPending ? <><Loader2 size={14} className="animate-spin" /> Генерация...</> : 'Сгенерировать план'}
              </button>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <AlertTriangle size={18} className="text-orange-500" />
              Анализ рисков
            </h3>
            {risksResult ? (
              <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto scrollbar-thin">
                {risksResult.risks}
              </div>
            ) : (
              <button
                onClick={() => risksMutation.mutate()}
                disabled={risksMutation.isPending}
                className="w-full border border-orange-300 text-orange-600 rounded-lg py-2 text-sm hover:bg-orange-50 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {risksMutation.isPending ? <><Loader2 size={14} className="animate-spin" /> Анализ...</> : 'Анализировать риски'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Tab 1: ITD Checklist */}
      {tab === 1 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <CheckSquare size={18} className="text-teal-500" />
              Чеклист ИТД
            </h3>
            {!itdChecklist && (
              <button
                onClick={() => checklistMutation.mutate()}
                disabled={checklistMutation.isPending}
                className="text-sm bg-teal-50 text-teal-700 px-3 py-1.5 rounded-lg hover:bg-teal-100 disabled:opacity-50"
              >
                {checklistMutation.isPending ? 'Загрузка...' : 'Загрузить чеклист'}
              </button>
            )}
          </div>
          {itdChecklist && (
            <div className="space-y-2">
              {itdChecklist.checklist.map((item, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-slate-100">
                  <span className={`mt-0.5 text-sm ${item.required ? 'text-red-500' : 'text-slate-400'}`}>
                    {item.required ? '●' : '○'}
                  </span>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-slate-800">{item.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {item.normative} · Фаза: {item.phase}
                    </div>
                    {item.note && <div className="text-xs text-slate-400 mt-0.5 italic">{item.note}</div>}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${item.required ? 'bg-red-50 text-red-600' : 'bg-slate-50 text-slate-500'}`}>
                    {item.required ? 'Обязательно' : 'Опционально'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Progress */}
      {tab === 2 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <TraceProgress projectId={id} />
        </div>
      )}

      {/* Tab 3: Work Sections */}
      {tab === 3 && <WorkSectionsTab projectId={id} />}

      {/* Tab 4: Documents */}
      {tab === 4 && (
        <div className="space-y-4">
          <div className="flex gap-3 flex-wrap">
            <button
              onClick={() => generateOjrMutation.mutate()}
              disabled={generateOjrMutation.isPending}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {generateOjrMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
              Создать ОЖР
            </button>
            <button
              onClick={() => generateKs11Mutation.mutate()}
              disabled={generateKs11Mutation.isPending}
              className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50"
            >
              {generateKs11Mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
              Создать КС-11
            </button>
          </div>

          <div className="bg-white rounded-xl border border-slate-200">
            <div className="px-5 py-4 border-b border-slate-100">
              <h3 className="font-semibold">Документы проекта</h3>
            </div>
            {documents.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <FileText size={40} className="mx-auto mb-2 opacity-30" />
                <p>Нет документов. Создайте первый документ.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-50">
                {documents.map(doc => (
                  <div key={doc.id} className="px-5 py-3 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-slate-800">{doc.title}</div>
                      <div className="text-xs text-slate-500">{doc.document_type} · {new Date(doc.created_at).toLocaleDateString('ru-RU')}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <a
                        href={`/api/documents/${doc.id}/download?format=pdf`}
                        className="text-xs text-blue-600 hover:underline"
                        target="_blank"
                        rel="noreferrer"
                      >
                        PDF
                      </a>
                      {doc.file_path && (
                        <a
                          href={documentsApi.download(doc.id)}
                          className="text-xs text-slate-500 hover:underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          DOCX
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 5: PDF Upload */}
      {tab === 5 && <PdfUploadTab projectId={id} />}
    </div>
  )
}

// ─── Таб разделов работ ───────────────────────────────────────────────────────

const STATUS_LABELS = {
  planned: { label: 'Запланирован', color: 'bg-slate-100 text-slate-600' },
  in_progress: { label: 'В работе', color: 'bg-blue-100 text-blue-700' },
  completed: { label: 'Завершён', color: 'bg-emerald-100 text-emerald-700' },
  accepted: { label: 'Принят', color: 'bg-green-100 text-green-800' },
  rejected: { label: 'Отклонён', color: 'bg-red-100 text-red-700' },
}

function WorkSectionsTab({ projectId }) {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)
  const [editPct, setEditPct] = useState(0)
  const [editStatus, setEditStatus] = useState('planned')
  const [form, setForm] = useState({ name: '', chainage_start: '', chainage_end: '', length_m: '', foreman: '', engineer: '' })

  const { data: sections = [], isLoading } = useQuery({
    queryKey: ['work-sections', projectId],
    queryFn: () => workSectionsApi.list(projectId).then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (data) => workSectionsApi.create({ project_id: projectId, ...data }),
    onSuccess: () => { queryClient.invalidateQueries(['work-sections', projectId]); setShowForm(false); setForm({ name: '', chainage_start: '', chainage_end: '', length_m: '', foreman: '', engineer: '' }) },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => workSectionsApi.update(id, data),
    onSuccess: () => { queryClient.invalidateQueries(['work-sections', projectId]); setEditId(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => workSectionsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries(['work-sections', projectId]),
  })

  if (isLoading) return <div className="text-center py-8 text-slate-400">Загрузка...</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-700">Разделы работ / Участки</h3>
        <button
          onClick={() => setShowForm(s => !s)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <Plus size={14} /> Добавить участок
        </button>
      </div>

      {showForm && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div className="col-span-2 md:col-span-3">
              <label className="text-xs text-slate-500 mb-1 block">Наименование *</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Укладка трубы, Сварка..." />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">ПК начало</label>
              <input value={form.chainage_start} onChange={e => setForm(f => ({ ...f, chainage_start: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="ПК 0+00" />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">ПК конец</label>
              <input value={form.chainage_end} onChange={e => setForm(f => ({ ...f, chainage_end: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="ПК 5+00" />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Длина, м</label>
              <input type="number" value={form.length_m} onChange={e => setForm(f => ({ ...f, length_m: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="500" />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Прораб</label>
              <input value={form.foreman} onChange={e => setForm(f => ({ ...f, foreman: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Инженер</label>
              <input value={form.engineer} onChange={e => setForm(f => ({ ...f, engineer: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm border rounded-lg hover:bg-slate-50">Отмена</button>
            <button
              onClick={() => createMut.mutate(form)}
              disabled={!form.name || createMut.isPending}
              className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {createMut.isPending ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </div>
      )}

      {sections.length === 0 && !showForm ? (
        <div className="text-center py-12 text-slate-400 bg-white rounded-xl border border-slate-200">
          <MapPin size={32} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">Нет разделов работ</p>
          <p className="text-sm mt-1">Добавьте участки трубопровода или виды работ</p>
        </div>
      ) : (
        <div className="space-y-2">
          {sections.map(s => {
            const st = STATUS_LABELS[s.status] || STATUS_LABELS.planned
            const isEdit = editId === s.id
            return (
              <div key={s.id} className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-slate-800 truncate">{s.name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.color}`}>{st.label}</span>
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-500 flex-wrap">
                      {(s.chainage_start || s.chainage_end) && (
                        <span className="flex items-center gap-1"><MapPin size={10} />{s.chainage_start} — {s.chainage_end}</span>
                      )}
                      {s.length_m && <span>{s.length_m} м</span>}
                      {s.foreman && <span className="flex items-center gap-1"><User size={10} />{s.foreman}</span>}
                    </div>
                    {/* Progress bar */}
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${s.progress_pct}%` }} />
                      </div>
                      <span className="text-xs text-slate-500 w-8 text-right">{s.progress_pct}%</span>
                    </div>
                    {isEdit && (
                      <div className="mt-3 flex items-center gap-3">
                        <select value={editStatus} onChange={e => setEditStatus(e.target.value)} className="border rounded-lg px-2 py-1 text-sm">
                          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                        </select>
                        <input type="range" min="0" max="100" value={editPct} onChange={e => setEditPct(+e.target.value)} className="w-28" />
                        <span className="text-sm text-slate-600 w-8">{editPct}%</span>
                        <button
                          onClick={() => updateMut.mutate({ id: s.id, data: { status: editStatus, progress_pct: editPct } })}
                          className="px-3 py-1 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                        >
                          <Check size={12} />
                        </button>
                        <button onClick={() => setEditId(null)} className="px-3 py-1 text-xs border rounded-lg hover:bg-slate-50">Отмена</button>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button
                      onClick={() => { setEditId(s.id); setEditPct(s.progress_pct); setEditStatus(s.status) }}
                      className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                      title="Редактировать"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => { if (confirm('Удалить раздел?')) deleteMut.mutate(s.id) }}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Таб загрузки PDF проектной документации ─────────────────────────────────

function PdfUploadTab({ projectId }) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('ППР')
  const [uploadProgress, setUploadProgress] = useState(null) // null | 'uploading' | 'done' | 'error'
  const [uploadError, setUploadError] = useState('')
  const [expandedId, setExpandedId] = useState(null)

  const { data: pdfs = [], isLoading, refetch } = useQuery({
    queryKey: ['project-pdfs', projectId],
    queryFn: () => shiftReportsApi.listPdfs(projectId).then(r => r.data),
    refetchInterval: (data) => {
      // Авто-обновление пока есть файлы без суммаризации
      const hasPending = data?.some(p => !p.text_summary)
      return hasPending ? 4000 : false
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (uploadId) =>
      shiftReportsApi.deletePdf
        ? shiftReportsApi.deletePdf(projectId, uploadId)
        : fetch(`/api/shift-reports/projects/${projectId}/pdfs/${uploadId}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries(['project-pdfs', projectId]),
  })

  const handleFiles = useCallback(async (files) => {
    const file = files[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Разрешены только PDF-файлы')
      return
    }
    setUploadError('')
    setUploadProgress('uploading')
    try {
      await shiftReportsApi.uploadPdf(projectId, file, selectedCategory)
      setUploadProgress('done')
      queryClient.invalidateQueries(['project-pdfs', projectId])
      setTimeout(() => setUploadProgress(null), 2500)
    } catch (e) {
      setUploadProgress('error')
      setUploadError(e?.response?.data?.detail || 'Ошибка загрузки')
    }
  }, [projectId, selectedCategory, queryClient])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const onFileChange = (e) => handleFiles(e.target.files)

  return (
    <div className="space-y-5">
      {/* Upload zone */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          <Upload size={18} className="text-blue-500" />
          Загрузить документ проекта
        </h3>

        {/* Category selector */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm text-slate-500">Категория:</span>
          {DOC_CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                selectedCategory === cat
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-slate-200 text-slate-600 hover:border-blue-300'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Drop zone */}
        <div
          onDrop={onDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onClick={() => fileInputRef.current?.click()}
          className={`
            border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
            ${dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={onFileChange}
          />

          {uploadProgress === 'uploading' ? (
            <div className="flex flex-col items-center gap-2 text-blue-600">
              <Loader2 size={36} className="animate-spin" />
              <p className="text-sm font-medium">Загрузка и извлечение текста...</p>
              <p className="text-xs text-slate-400">AI-суммаризация запустится в фоне</p>
            </div>
          ) : uploadProgress === 'done' ? (
            <div className="flex flex-col items-center gap-2 text-green-600">
              <CheckCircle2 size={36} />
              <p className="text-sm font-medium">Файл загружен</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-slate-400">
              <Upload size={36} className={dragOver ? 'text-blue-500' : ''} />
              <p className="text-sm font-medium text-slate-600">
                Перетащите PDF сюда или нажмите для выбора
              </p>
              <p className="text-xs">ПОС · ППР · ПД · НТД · Экспертные заключения</p>
            </div>
          )}
        </div>

        {uploadError && (
          <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 rounded-lg px-3 py-2">
            <X size={14} />
            {uploadError}
          </div>
        )}
      </div>

      {/* Uploaded PDFs list */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 flex items-center gap-2">
            <BookOpen size={16} className="text-slate-500" />
            Загруженные документы
            {pdfs.length > 0 && (
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {pdfs.length}
              </span>
            )}
          </h3>
          {isLoading && <Loader2 size={16} className="animate-spin text-slate-400" />}
        </div>

        {pdfs.length === 0 ? (
          <div className="p-10 text-center text-slate-400">
            <BookOpen size={36} className="mx-auto mb-2 opacity-30" />
            <p className="text-sm">Нет загруженных документов</p>
            <p className="text-xs mt-1">Загрузите ПОС, ППР или ПД — AI извлечёт параметры проекта и поможет заполнять рапорты</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {pdfs.map(pdf => (
              <PdfRow
                key={pdf.id}
                pdf={pdf}
                expanded={expandedId === pdf.id}
                onToggle={() => setExpandedId(expandedId === pdf.id ? null : pdf.id)}
                onDelete={() => deleteMutation.mutate(pdf.id)}
                isDeleting={deleteMutation.isPending && deleteMutation.variables === pdf.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Строка с загруженным PDF ─────────────────────────────────────────────────

function PdfRow({ pdf, expanded, onToggle, onDelete, isDeleting }) {
  const uploadedAt = pdf.uploaded_at
    ? new Date(pdf.uploaded_at).toLocaleDateString('ru-RU')
    : '—'

  const hasSummary = !!pdf.text_summary
  const phases = pdf.phases_detected || []

  return (
    <div>
      <div className="flex items-center gap-3 px-5 py-3">
        <FileCheck size={18} className="text-blue-500 shrink-0" />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-800 truncate">{pdf.filename}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 shrink-0">
              {pdf.doc_category}
            </span>
            {!hasSummary && (
              <span className="text-xs flex items-center gap-1 text-amber-600">
                <Loader2 size={10} className="animate-spin" /> AI анализирует...
              </span>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            {pdf.page_count} стр. · {Math.round((pdf.chars_extracted || 0) / 1000)} тыс. символов · {uploadedAt}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onToggle}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="p-1.5 text-slate-300 hover:text-red-500 rounded-lg hover:bg-red-50 disabled:opacity-50"
          >
            {isDeleting ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-5 pb-4 space-y-3 border-t border-slate-50 pt-3 bg-slate-50/50">
          {/* Detected phases */}
          {phases.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">
                Обнаруженные фазы строительства
              </p>
              <div className="flex flex-wrap gap-1.5">
                {phases.map(p => (
                  <span key={p} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* AI Summary */}
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">
              Краткое содержание (AI)
            </p>
            {hasSummary ? (
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {pdf.text_summary}
              </p>
            ) : (
              <div className="flex items-center gap-2 text-amber-600 text-sm">
                <Loader2 size={14} className="animate-spin" />
                Claude анализирует документ... обновится автоматически
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef, useCallback } from 'react'
import { projectsApi, documentsApi, shiftReportsApi } from '../utils/api'
import {
  FileText, Loader2, CheckSquare, BarChart2, AlertTriangle,
  ClipboardList, Upload, Trash2, BookOpen, ChevronDown, ChevronUp,
  FileCheck, X, CheckCircle2, TrendingUp,
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

const TAB_LABELS = ['Обзор', 'ИТД', 'Прогресс', 'Документы', 'ПД/ППР']

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
          <Link
            to={`/projects/${id}/shift-reports`}
            className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors shrink-0"
          >
            <ClipboardList size={16} />
            Сменные рапорты
          </Link>
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

      {/* Tab 3: Documents */}
      {tab === 3 && (
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

      {/* Tab 4: PDF Upload */}
      {tab === 4 && <PdfUploadTab projectId={id} />}
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

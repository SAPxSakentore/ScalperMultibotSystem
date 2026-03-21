import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { projectsApi, documentsApi } from '../utils/api'
import { FileText, Loader2, CheckSquare, BarChart2, AlertTriangle, ClipboardList } from 'lucide-react'

const TAB_LABELS = ['Обзор', 'ИТД', 'Анализ', 'Документы']

export default function ProjectDetail() {
  const { id } = useParams()
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
  })

  const generateKs11Mutation = useMutation({
    mutationFn: () => documentsApi.generateKs11(id),
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
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1 w-fit">
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
          {/* Plan */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <BarChart2 size={18} className="text-blue-500" />
              План проекта (ГИП Бекенов Н.А.)
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

          {/* Risks */}
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

      {/* Tab 2: Analysis */}
      {tab === 2 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 text-sm text-slate-500">
          Расширенный анализ проекта — в разработке
        </div>
      )}

      {/* Tab 3: Documents */}
      {tab === 3 && (
        <div className="space-y-4">
          <div className="flex gap-3">
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
                    {doc.file_path && (
                      <a
                        href={documentsApi.download(doc.id)}
                        className="text-xs text-blue-600 hover:underline"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Скачать .docx
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

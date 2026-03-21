import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ClipboardList, Plus, CheckCircle2, FileText,
  ChevronDown, ChevronUp, Loader2, AlertCircle, Download,
} from 'lucide-react'
import { shiftReportsApi, projectsApi } from '../utils/api'
import TraceProgress from '../components/TraceProgress'

const SHIFT_LABELS = { day: 'Дневная', night: 'Ночная' }

const STATUS_BADGE = (finalized) =>
  finalized
    ? 'bg-green-100 text-green-700 border border-green-200'
    : 'bg-yellow-100 text-yellow-700 border border-yellow-200'

export default function ShiftReports() {
  const { id: projectId } = useParams()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [finalizeResult, setFinalizeResult] = useState(null)
  const [signerName, setSignerName] = useState('')

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId).then(r => r.data),
    enabled: !!projectId,
  })

  const { data: phases = [] } = useQuery({
    queryKey: ['shift-phases'],
    queryFn: () => shiftReportsApi.phases().then(r => r.data),
  })

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['shift-reports', projectId],
    queryFn: () => shiftReportsApi.list(projectId).then(r => r.data),
    enabled: !!projectId,
  })

  const createMutation = useMutation({
    mutationFn: (data) => shiftReportsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['shift-reports', projectId])
      setShowForm(false)
    },
  })

  const finalizeMutation = useMutation({
    mutationFn: ({ reportId, signer }) => shiftReportsApi.finalize(reportId, signer),
    onSuccess: (res) => {
      queryClient.invalidateQueries(['shift-reports', projectId])
      setFinalizeResult(res.data)
    },
  })

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <ClipboardList size={24} className="text-blue-600" />
            Сменные рапорты
          </h2>
          {project && (
            <p className="text-slate-500 mt-1">{project.code} — {project.name}</p>
          )}
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          <Plus size={16} /> Новый рапорт
        </button>
      </div>

      {/* Прогресс по трассе (компактный) */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <TraceProgress projectId={projectId} compact />
      </div>

      {/* Форма создания рапорта */}
      {showForm && (
        <CreateReportForm
          projectId={projectId}
          phases={phases}
          onSubmit={(data) => createMutation.mutate(data)}
          isLoading={createMutation.isPending}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Результат финализации */}
      {finalizeResult && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4">
          <div className="flex items-center gap-2 text-green-700 font-semibold mb-2">
            <CheckCircle2 size={18} />
            Рапорт финализирован — ИТД сгенерировано
          </div>
          <ul className="space-y-1">
            {finalizeResult.generated_documents?.map((doc) => (
              <li key={doc.id} className="flex items-center gap-2 text-sm text-green-800">
                <FileText size={14} />
                {doc.title}
                <a
                  href={`/api/documents/${doc.id}/download?format=pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-auto flex items-center gap-1 text-green-600 hover:underline"
                >
                  <Download size={12} /> PDF
                </a>
              </li>
            ))}
          </ul>
          <button
            onClick={() => setFinalizeResult(null)}
            className="mt-3 text-xs text-slate-400 hover:text-slate-600"
          >
            Закрыть
          </button>
        </div>
      )}

      {/* Список рапортов */}
      {isLoading ? (
        <div className="flex justify-center py-12 text-slate-400">
          <Loader2 size={24} className="animate-spin" />
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-slate-400">
          <ClipboardList size={40} className="mx-auto mb-3 opacity-30" />
          <p>Рапортов пока нет. Создайте первый рапорт.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <ReportCard
              key={r.id}
              report={r}
              phases={phases}
              expanded={expandedId === r.id}
              onToggle={() => setExpandedId(expandedId === r.id ? null : r.id)}
              signerName={signerName}
              onSignerChange={setSignerName}
              onFinalize={() => finalizeMutation.mutate({ reportId: r.id, signer: signerName })}
              isFinalizing={finalizeMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Карточка рапорта ─────────────────────────────────────────────────────────

function ReportCard({ report, phases, expanded, onToggle, signerName, onSignerChange, onFinalize, isFinalizing }) {
  const phaseLabel = phases.find(p => p.value === report.construction_phase)?.name_ru
    || report.construction_phase || '—'

  const dateStr = report.shift_date
    ? new Date(report.shift_date).toLocaleDateString('ru-RU')
    : '—'

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Шапка */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 p-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-semibold text-slate-800">{dateStr}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
              {SHIFT_LABELS[report.shift_number] || report.shift_number}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_BADGE(report.is_finalized)}`}>
              {report.is_finalized ? 'Финализирован' : 'Черновик'}
            </span>
            {report.ai_generated && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                AI
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-0.5 truncate">{phaseLabel}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-sm text-slate-600">
            {report.chainage_start || '—'} — {report.chainage_end || '—'}
          </p>
          <p className="text-xs text-slate-400">{report.length_done_m || 0} м</p>
        </div>
        {expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>

      {/* Детали */}
      {expanded && (
        <div className="border-t border-slate-100 p-4 space-y-4">
          {/* Погода и прораб */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <InfoBlock label="Прораб" value={report.shift_foreman || '—'} />
            <InfoBlock label="Погода (утро)" value={report.weather_morning || '—'} />
            <InfoBlock label="Погода (день)" value={report.weather_afternoon || '—'} />
            <InfoBlock label="Простой" value={report.downtime_hours ? `${report.downtime_hours} ч` : '0 ч'} />
          </div>

          {/* Работы */}
          {report.works_done?.length > 0 && (
            <Section title="Выполненные работы">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-500 text-xs border-b border-slate-100">
                    <th className="text-left py-1 pr-3">Вид работы</th>
                    <th className="text-right py-1 pr-3">Кол-во</th>
                    <th className="text-right py-1">Ед.</th>
                  </tr>
                </thead>
                <tbody>
                  {report.works_done.map((w, i) => (
                    <tr key={i} className="border-b border-slate-50">
                      <td className="py-1 pr-3">{w.work_type || '—'}</td>
                      <td className="text-right pr-3">{w.quantity ?? '—'}</td>
                      <td className="text-right">{w.unit || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>
          )}

          {/* Техника */}
          {report.machinery_on_site?.length > 0 && (
            <Section title="Техника на объекте">
              <div className="flex flex-wrap gap-2">
                {report.machinery_on_site.map((m, i) => (
                  <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full">
                    {m.name || m} {m.hours_worked ? `· ${m.hours_worked} ч` : ''}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Контроль качества */}
          {report.quality_checks?.length > 0 && (
            <Section title="Контроль качества">
              {report.quality_checks.map((qc, i) => (
                <div key={i} className="text-sm text-slate-600">
                  {qc.type || qc}: {qc.result || ''}
                </div>
              ))}
            </Section>
          )}

          {/* Задание на следующую смену */}
          {report.next_shift_plan && (
            <Section title="Задание на следующую смену">
              <p className="text-sm text-slate-600">{report.next_shift_plan}</p>
            </Section>
          )}

          {/* Сгенерированные документы */}
          {report.documents_issued?.length > 0 && (
            <Section title="Выданные ИТД-документы">
              {report.documents_issued.map((d, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-slate-700">
                  <FileText size={14} className="text-green-600" />
                  {d.title || d.type}
                  {d.doc_id && (
                    <a
                      href={`/api/documents/${d.doc_id}/download?format=pdf`}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-auto flex items-center gap-1 text-blue-600 hover:underline text-xs"
                    >
                      <Download size={12} /> PDF
                    </a>
                  )}
                </div>
              ))}
            </Section>
          )}

          {/* Кнопки действий */}
          <div className="flex items-center gap-3 pt-2 border-t border-slate-100">
            <a
              href={shiftReportsApi.download(report.id)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
            >
              <Download size={14} /> Скачать рапорт PDF
            </a>

            {!report.is_finalized && (
              <div className="flex items-center gap-2 ml-auto">
                <input
                  type="text"
                  placeholder="ФИО подписанта"
                  value={signerName}
                  onChange={(e) => onSignerChange(e.target.value)}
                  className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 w-44 focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
                <button
                  onClick={onFinalize}
                  disabled={isFinalizing}
                  className="flex items-center gap-2 px-4 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {isFinalizing
                    ? <Loader2 size={14} className="animate-spin" />
                    : <CheckCircle2 size={14} />}
                  Финализировать + ИТД
                </button>
              </div>
            )}

            {report.is_finalized && report.signed_by && (
              <span className="ml-auto text-xs text-slate-400">
                Подписал: {report.signed_by} · {report.signed_at
                  ? new Date(report.signed_at).toLocaleDateString('ru-RU')
                  : ''}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Форма создания рапорта ───────────────────────────────────────────────────

function CreateReportForm({ projectId, phases, onSubmit, isLoading, onCancel }) {
  const today = new Date().toISOString().slice(0, 16)
  const [form, setForm] = useState({
    project_id: projectId,
    shift_date: today,
    shift_number: 'day',
    construction_phase: phases[0]?.value || '',
    shift_foreman: '',
    chainage_start: '',
    chainage_end: '',
    length_done_m: 0,
    weather_morning: '',
    weather_afternoon: '',
    use_ai: true,
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ ...form, shift_date: new Date(form.shift_date).toISOString() })
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-xl border border-slate-200 p-5 space-y-4"
    >
      <h3 className="font-semibold text-slate-800">Новый сменный рапорт</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Дата и время">
          <input
            type="datetime-local"
            value={form.shift_date}
            onChange={e => set('shift_date', e.target.value)}
            className="input"
            required
          />
        </Field>
        <Field label="Смена">
          <select value={form.shift_number} onChange={e => set('shift_number', e.target.value)} className="input">
            <option value="day">Дневная</option>
            <option value="night">Ночная</option>
          </select>
        </Field>
        <Field label="Фаза строительства">
          <select value={form.construction_phase} onChange={e => set('construction_phase', e.target.value)} className="input" required>
            {phases.map(p => <option key={p.value} value={p.value}>{p.name_ru}</option>)}
          </select>
        </Field>
        <Field label="Прораб / начальник смены">
          <input
            type="text"
            value={form.shift_foreman}
            onChange={e => set('shift_foreman', e.target.value)}
            placeholder="ФИО"
            className="input"
          />
        </Field>
        <Field label="ПК начало">
          <input type="text" value={form.chainage_start} onChange={e => set('chainage_start', e.target.value)} placeholder="напр. ПК 14+00" className="input" />
        </Field>
        <Field label="ПК конец">
          <input type="text" value={form.chainage_end} onChange={e => set('chainage_end', e.target.value)} placeholder="напр. ПК 15+20" className="input" />
        </Field>
        <Field label="Выполнено, м">
          <input type="number" value={form.length_done_m} onChange={e => set('length_done_m', parseFloat(e.target.value) || 0)} className="input" min="0" />
        </Field>
        <Field label="Погода (утро)">
          <input type="text" value={form.weather_morning} onChange={e => set('weather_morning', e.target.value)} placeholder="+5°C, ветер 3 м/с" className="input" />
        </Field>
        <Field label="Погода (день)">
          <input type="text" value={form.weather_afternoon} onChange={e => set('weather_afternoon', e.target.value)} placeholder="+8°C, ясно" className="input" />
        </Field>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
        <input
          type="checkbox"
          checked={form.use_ai}
          onChange={e => set('use_ai', e.target.checked)}
          className="rounded"
        />
        Заполнить остальные поля через AI (Claude)
      </label>

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
        >
          {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          {isLoading ? 'Создаётся...' : 'Создать рапорт'}
        </button>
        <button type="button" onClick={onCancel} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800">
          Отмена
        </button>
      </div>
    </form>
  )
}

// ─── Вспомогательные компоненты ───────────────────────────────────────────────

function Field({ label, children }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</label>
      {children}
    </div>
  )
}

function InfoBlock({ label, value }) {
  return (
    <div>
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-slate-700 font-medium">{value}</p>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">{title}</p>
      {children}
    </div>
  )
}

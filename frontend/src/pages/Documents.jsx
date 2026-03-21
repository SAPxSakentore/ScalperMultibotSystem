import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileText, Download, Loader2, Sparkles, CheckCircle2,
  AlertCircle, ChevronDown, Shield, TestTube2, BookOpen,
  FileCheck, Package, Scale, FileSearch, RefreshCw,
} from 'lucide-react'
import { projectsApi, documentsApi } from '../utils/api'

// ─── Справочники ─────────────────────────────────────────────────────────────

const DOC_GROUPS = [
  {
    label: 'Журналы',
    icon: BookOpen,
    types: ['ojr', 'welding_journal', 'isolation_journal', 'geodesy_journal'],
  },
  {
    label: 'Акты освидетельствования (АОСР)',
    icon: FileCheck,
    types: ['aosr', 'intermediate_acceptance'],
  },
  {
    label: 'Испытания',
    icon: TestTube2,
    types: ['hydraulic_test', 'pneumatic_test', 'purge_act', 'tightness_test'],
  },
  {
    label: 'Акты приёмки',
    icon: CheckCircle2,
    types: ['ks2', 'ks3', 'ks11', 'ks14'],
  },
  {
    label: 'Исполнительная документация',
    icon: FileText,
    types: ['executive_scheme', 'building_passport'],
  },
  {
    label: 'Проектная документация (ПД/РД)',
    icon: FileSearch,
    types: ['pos', 'por', 'ppr'],
  },
  {
    label: 'Технологические карты',
    icon: FileText,
    types: ['tech_card'],
  },
  {
    label: 'Сертификаты и паспорта',
    icon: Package,
    types: ['material_cert', 'equipment_passport', 'welder_cert'],
  },
  {
    label: 'Разрешения и ввод',
    icon: Scale,
    types: ['construction_permit', 'commissioning_act'],
  },
  {
    label: 'Прочее',
    icon: FileText,
    types: ['other'],
  },
]

const TYPE_LABELS = {
  ojr: 'Общий журнал работ',
  welding_journal: 'Журнал сварочных работ',
  isolation_journal: 'Журнал изоляционных работ',
  geodesy_journal: 'Геодезический журнал',
  aosr: 'АОСР',
  intermediate_acceptance: 'Акт промежуточной приёмки',
  hydraulic_test: 'Акт гидравлических испытаний',
  pneumatic_test: 'Акт пневматических испытаний',
  purge_act: 'Акт продувки',
  tightness_test: 'Акт на герметичность',
  executive_scheme: 'Исполнительная схема',
  building_passport: 'Строительный паспорт',
  ks2: 'КС-2',
  ks3: 'КС-3',
  ks11: 'КС-11',
  ks14: 'КС-14',
  pos: 'ПОС',
  por: 'ПОР',
  ppr: 'ППР',
  tech_card: 'Технологическая карта',
  material_cert: 'Сертификат на материал',
  equipment_passport: 'Паспорт оборудования',
  welder_cert: 'Удостоверение сварщика',
  construction_permit: 'Разрешение на строительство',
  commissioning_act: 'Акт ввода в эксплуатацию',
  other: 'Прочее',
}

const STATUS_STYLES = {
  draft:    'bg-slate-100 text-slate-600',
  review:   'bg-amber-100 text-amber-700',
  approved: 'bg-blue-100 text-blue-700',
  signed:   'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  archived: 'bg-slate-200 text-slate-500',
}

const STATUS_LABELS = {
  draft: 'Черновик', review: 'На проверке', approved: 'Утверждён',
  signed: 'Подписан', rejected: 'Отклонён', archived: 'Архив',
}

// ─── Модалки ─────────────────────────────────────────────────────────────────

function ModalAosr({ projectId, onClose, onSuccess }) {
  const [form, setForm] = useState({
    work_name: '', chainage: '', work_date: '', act_number: '',
    foreman: '', author_supervisor: '', next_works: '',
  })
  const mutation = useMutation({
    mutationFn: () => documentsApi.generateAosr({ project_id: projectId, ...form }),
    onSuccess: (res) => { onSuccess(res.data); onClose() },
  })
  const f = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }))

  return (
    <ModalShell title="Сформировать АОСР" onClose={onClose}>
      <div className="grid grid-cols-2 gap-3 text-sm">
        {[
          ['work_name', 'Наименование скрытой работы *', 'col-span-2'],
          ['chainage', 'Пикетаж (ПК __ +__)'],
          ['work_date', 'Дата выполнения работ'],
          ['act_number', 'Номер акта'],
          ['foreman', 'Производитель работ'],
          ['author_supervisor', 'Технический надзор'],
          ['next_works', 'Последующие работы', 'col-span-2'],
        ].map(([key, label, cls]) => (
          <label key={key} className={`flex flex-col gap-1 ${cls || ''}`}>
            <span className="text-slate-500">{label}</span>
            <input
              value={form[key]}
              onChange={f(key)}
              className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </label>
        ))}
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-lg">Отмена</button>
        <button
          onClick={() => mutation.mutate()}
          disabled={!form.work_name || mutation.isPending}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          Сформировать
        </button>
      </div>
    </ModalShell>
  )
}

function ModalHydraulicTest({ projectId, onClose, onSuccess }) {
  const [form, setForm] = useState({
    section_chainage: '', length_m: '', wall_thickness_mm: '',
    steel_grade: '', test_pressure_mpa: '', tightness_pressure_mpa: '',
    test_date: '', duration_hours: '24', result: 'УДОВЛЕТВОРИТЕЛЬНО',
  })
  const mutation = useMutation({
    mutationFn: () => documentsApi.generateHydraulicTest({
      project_id: projectId,
      ...form,
      length_m: parseFloat(form.length_m) || 0,
      wall_thickness_mm: parseFloat(form.wall_thickness_mm) || 0,
      test_pressure_mpa: parseFloat(form.test_pressure_mpa) || 0,
      tightness_pressure_mpa: parseFloat(form.tightness_pressure_mpa) || 0,
      duration_hours: parseInt(form.duration_hours) || 24,
    }),
    onSuccess: (res) => { onSuccess(res.data); onClose() },
  })
  const f = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }))

  return (
    <ModalShell title="Акт гидравлических испытаний" onClose={onClose}>
      <div className="grid grid-cols-2 gap-3 text-sm">
        {[
          ['section_chainage', 'Участок (ПК __ - ПК __)'],
          ['test_date', 'Дата испытания'],
          ['length_m', 'Длина участка, м'],
          ['wall_thickness_mm', 'Толщина стенки, мм'],
          ['steel_grade', 'Марка стали'],
          ['duration_hours', 'Продолжительность, ч'],
          ['test_pressure_mpa', 'Испытательное давление, МПа'],
          ['tightness_pressure_mpa', 'Давление на герметичность, МПа'],
          ['result', 'Результат', 'col-span-2'],
        ].map(([key, label, cls]) => (
          <label key={key} className={`flex flex-col gap-1 ${cls || ''}`}>
            <span className="text-slate-500">{label}</span>
            <input
              value={form[key]}
              onChange={f(key)}
              className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </label>
        ))}
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-lg">Отмена</button>
        <button
          onClick={() => mutation.mutate()}
          disabled={!form.section_chainage || mutation.isPending}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          Сформировать
        </button>
      </div>
    </ModalShell>
  )
}

function ModalPpr({ projectId, onClose, onSuccess }) {
  const [method, setMethod] = useState('открытая траншея')
  const methods = ['открытая траншея', 'ГНБ (горизонтально-направленное бурение)', 'надземная прокладка', 'микротоннелирование']
  const mutation = useMutation({
    mutationFn: () => documentsApi.generatePpr({ project_id: projectId, installation_method: method }),
    onSuccess: (res) => { onSuccess(res.data); onClose() },
  })
  return (
    <ModalShell title="Сформировать ППР" onClose={onClose}>
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-slate-500">Метод прокладки трубопровода</span>
        <select
          value={method}
          onChange={e => setMethod(e.target.value)}
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          {methods.map(m => <option key={m}>{m}</option>)}
        </select>
      </label>
      <p className="text-xs text-slate-400 mt-2">
        Будет сформирован полный ППР: последовательность фаз, состав механизмов, ОТ и ПБ,
        ООС, перечень технологических карт (ТК-01…ТК-20) — ~40 стр. DOCX.
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-lg">Отмена</button>
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          Сформировать ППР
        </button>
      </div>
    </ModalShell>
  )
}

function ModalTechCard({ projectId, onClose, onSuccess }) {
  const [phase, setPhase] = useState('')
  const [cardNo, setCardNo] = useState('1')
  const [scope, setScope] = useState('')

  const { data: phases = [] } = useQuery({
    queryKey: ['doc-phases'],
    queryFn: () => documentsApi.phases().then(r => r.data),
  })

  const mutation = useMutation({
    mutationFn: () => documentsApi.generateTechCard({
      project_id: projectId,
      phase,
      card_number: parseInt(cardNo) || 1,
      custom_scope: scope,
    }),
    onSuccess: (res) => { onSuccess(res.data); onClose() },
  })

  return (
    <ModalShell title="Технологическая карта (техкарта)" onClose={onClose}>
      <div className="space-y-3 text-sm">
        <label className="flex flex-col gap-1">
          <span className="text-slate-500">Вид работ / фаза строительства *</span>
          <select
            value={phase}
            onChange={e => setPhase(e.target.value)}
            className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <option value="">— выберите —</option>
            {phases.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </label>
        <div className="flex gap-3">
          <label className="flex flex-col gap-1 w-24">
            <span className="text-slate-500">Номер ТК</span>
            <input
              type="number" min="1" max="99"
              value={cardNo}
              onChange={e => setCardNo(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </label>
          <label className="flex flex-col gap-1 flex-1">
            <span className="text-slate-500">Особые условия (необязательно)</span>
            <input
              value={scope}
              onChange={e => setScope(e.target.value)}
              placeholder="напр. обводнённый грунт, скала"
              className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </label>
        </div>
        <p className="text-xs text-slate-400">
          Карта включает: персонал, машины и механизмы, последовательность операций,
          контроль качества (входной / операционный / приёмочный), требования ОТ и ПБ, НТД.
        </p>
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-500 hover:bg-slate-100 rounded-lg">Отмена</button>
        <button
          onClick={() => mutation.mutate()}
          disabled={!phase || mutation.isPending}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          Сформировать техкарту
        </button>
      </div>
    </ModalShell>
  )
}

function ModalShell({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-800 text-base">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl leading-none">×</button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ─── Строка документа ─────────────────────────────────────────────────────────

function DocRow({ doc, onAiCheck }) {
  const [aiResult, setAiResult] = useState(null)
  const [checking, setChecking] = useState(false)

  async function handleAiCheck() {
    setChecking(true)
    try {
      const res = await documentsApi.checkWithAi(doc.id)
      setAiResult(res.data.review)
    } catch {
      setAiResult('Ошибка при проверке')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="border border-slate-100 rounded-xl p-3 space-y-2 hover:border-slate-200 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-800 truncate">{doc.title}</span>
            {doc.document_number && (
              <span className="text-xs text-slate-400">#{doc.document_number}</span>
            )}
            {doc.auto_generated && (
              <span className="flex items-center gap-1 text-xs bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded-md">
                <Sparkles size={10} /> AI
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
            <span className={`px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[doc.status] || ''}`}>
              {STATUS_LABELS[doc.status] || doc.status}
            </span>
            <span>{new Date(doc.created_at).toLocaleDateString('ru-RU')}</span>
            {doc.normative_refs?.length > 0 && (
              <span className="truncate max-w-[200px]">{doc.normative_refs.slice(0, 2).join(', ')}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {/* Скачать DOCX */}
          <a
            href={`${documentsApi.download(doc.id)}?format=docx`}
            target="_blank"
            rel="noreferrer"
            title="Скачать DOCX"
            className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            <Download size={15} />
          </a>
          {/* Скачать PDF */}
          <a
            href={`${documentsApi.download(doc.id)}?format=pdf`}
            target="_blank"
            rel="noreferrer"
            title="Скачать PDF"
            className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          >
            <FileText size={15} />
          </a>
          {/* Проверить AI */}
          <button
            onClick={handleAiCheck}
            disabled={checking}
            title="Проверить через AI"
            className="p-1.5 text-slate-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors disabled:opacity-50"
          >
            {checking ? <Loader2 size={15} className="animate-spin" /> : <Shield size={15} />}
          </button>
        </div>
      </div>

      {/* AI-проверка результат */}
      {aiResult && (
        <div className="text-xs bg-purple-50 text-purple-800 rounded-lg px-3 py-2 leading-relaxed">
          {aiResult}
        </div>
      )}
    </div>
  )
}

// ─── Группа документов ────────────────────────────────────────────────────────

function DocGroup({ group, docs }) {
  const [open, setOpen] = useState(true)
  const Icon = group.icon

  if (docs.length === 0) return null

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-slate-500" />
          <span className="font-medium text-slate-700 text-sm">{group.label}</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{docs.length}</span>
        </div>
        <ChevronDown size={16} className={`text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-2">
          {docs.map(doc => <DocRow key={doc.id} doc={doc} />)}
        </div>
      )}
    </div>
  )
}

// ─── Главный компонент ────────────────────────────────────────────────────────

export default function Documents() {
  const [projectId, setProjectId] = useState('')
  const [modal, setModal] = useState(null) // 'aosr' | 'hydraulic' | 'ppr' | 'techcard'
  const queryClient = useQueryClient()

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(r => r.data),
  })

  const { data: docs = [], isLoading, refetch } = useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => documentsApi.list(projectId).then(r => r.data),
    enabled: !!projectId,
  })

  const project = projects.find(p => p.id === projectId)

  // Генерация ОЖР
  const ojrMut = useMutation({
    mutationFn: () => documentsApi.generateOjr({ project_id: projectId }),
    onSuccess: () => queryClient.invalidateQueries(['documents', projectId]),
  })

  // Генерация ППР
  const pprMut = useMutation({
    mutationFn: (opts) => documentsApi.generatePpr({ project_id: projectId, ...opts }),
    onSuccess: () => queryClient.invalidateQueries(['documents', projectId]),
  })

  // Пакет всех технологических карт (ZIP)
  const bundleMut = useMutation({
    mutationFn: () => documentsApi.generateTechCardsBundle({ project_id: projectId }),
    onSuccess: (res) => {
      queryClient.invalidateQueries(['documents', projectId])
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `TechCards_${projectId}.zip`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  // Генерация КС-11
  const ks11Mut = useMutation({
    mutationFn: () => documentsApi.generateKs11(projectId),
    onSuccess: () => queryClient.invalidateQueries(['documents', projectId]),
  })

  // Группируем документы
  const grouped = DOC_GROUPS.map(group => ({
    group,
    docs: docs.filter(d => group.types.includes(d.document_type)),
  }))

  const stats = {
    total: docs.length,
    signed: docs.filter(d => d.status === 'signed').length,
    ai: docs.filter(d => d.auto_generated).length,
    draft: docs.filter(d => d.status === 'draft').length,
  }

  function handleModalSuccess() {
    queryClient.invalidateQueries(['documents', projectId])
  }

  return (
    <div className="space-y-5">
      {/* Заголовок */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <FileText size={24} className="text-blue-600" />
            Документация ИТД
          </h2>
          <p className="text-slate-500 mt-0.5 text-sm">Исполнительно-техническая документация проекта</p>
        </div>

        {/* Выбор проекта */}
        <div className="relative">
          <select
            value={projectId}
            onChange={e => setProjectId(e.target.value)}
            className="appearance-none border border-slate-200 rounded-xl px-4 py-2 pr-9 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-300 text-slate-700 min-w-[240px]"
          >
            <option value="">— Выберите проект —</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.code} / {p.name}</option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>
      </div>

      {!projectId && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400">
          <FileText size={48} className="mx-auto mb-3 opacity-20" />
          <p className="text-sm">Выберите проект для просмотра документации</p>
        </div>
      )}

      {projectId && (
        <>
          {/* Статистика + кнопки генерации */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Всего документов', value: stats.total, color: 'text-slate-800' },
              { label: 'Подписано', value: stats.signed, color: 'text-green-700' },
              { label: 'Сгенерировано AI', value: stats.ai, color: 'text-purple-700' },
              { label: 'Черновики', value: stats.draft, color: 'text-amber-700' },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-slate-200 px-4 py-3">
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Панель генерации */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-purple-500" />
              <span className="text-sm font-medium text-slate-700">Сформировать документ</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <GenButton
                label="ОЖР"
                loading={ojrMut.isPending}
                onClick={() => ojrMut.mutate()}
                title="Общий журнал работ"
              />
              <GenButton
                label="АОСР"
                onClick={() => setModal('aosr')}
                title="Акт освидетельствования скрытых работ"
              />
              <GenButton
                label="Гидроиспытания"
                onClick={() => setModal('hydraulic')}
                title="Акт гидравлических испытаний"
              />
              <GenButton
                label="КС-11"
                loading={ks11Mut.isPending}
                onClick={() => ks11Mut.mutate()}
                title="Акт приёмки построенного объекта"
              />
              <div className="w-px bg-slate-200 self-stretch mx-1" />
              <GenButton
                label="ППР"
                onClick={() => setModal('ppr')}
                title="Проект производства работ (все 20 фаз)"
              />
              <GenButton
                label="Техкарта"
                onClick={() => setModal('techcard')}
                title="Технологическая карта на отдельный вид работ"
              />
              <GenButton
                label="Весь пакет ТК"
                loading={bundleMut.isPending}
                onClick={() => bundleMut.mutate()}
                title="Сформировать все 20 технологических карт (ZIP)"
              />
              <button
                onClick={() => refetch()}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <RefreshCw size={13} /> Обновить
              </button>
            </div>
          </div>

          {/* Список документов */}
          {isLoading ? (
            <div className="flex justify-center py-12 text-slate-400">
              <Loader2 size={24} className="animate-spin" />
            </div>
          ) : docs.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-10 text-center">
              <AlertCircle size={36} className="mx-auto mb-3 text-slate-300" />
              <p className="text-slate-500 text-sm">
                Документов нет. Создайте сменные рапорты и финализируйте их — ИТД сформируется автоматически.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {grouped.map(({ group, docs: gDocs }) => (
                <DocGroup key={group.label} group={group} docs={gDocs} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Модалки */}
      {modal === 'ppr' && (
        <ModalPpr
          projectId={projectId}
          onClose={() => setModal(null)}
          onSuccess={handleModalSuccess}
        />
      )}
      {modal === 'techcard' && (
        <ModalTechCard
          projectId={projectId}
          onClose={() => setModal(null)}
          onSuccess={handleModalSuccess}
        />
      )}
      {modal === 'aosr' && (
        <ModalAosr
          projectId={projectId}
          onClose={() => setModal(null)}
          onSuccess={handleModalSuccess}
        />
      )}
      {modal === 'hydraulic' && (
        <ModalHydraulicTest
          projectId={projectId}
          onClose={() => setModal(null)}
          onSuccess={handleModalSuccess}
        />
      )}
    </div>
  )
}

function GenButton({ label, loading, onClick, title }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      title={title}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 rounded-lg transition-colors disabled:opacity-50"
    >
      {loading
        ? <Loader2 size={13} className="animate-spin" />
        : <Sparkles size={13} className="text-purple-500" />
      }
      {label}
    </button>
  )
}

import { useQuery } from '@tanstack/react-query'
import { statsApi } from '../utils/api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { BarChart2, FileText, ClipboardList, FolderOpen } from 'lucide-react'

const STATUS_RU = {
  initiation: 'Инициация',
  design: 'Проектирование',
  permits: 'Согласования',
  procurement: 'Закупки',
  construction: 'Строительство',
  testing: 'Испытания',
  commissioning: 'Пуско-наладка',
  acceptance: 'Приёмка',
  completed: 'Завершён',
  suspended: 'Приостановлен',
}

const TYPE_RU = {
  gas_pipeline_high: 'Газопровод ВД',
  gas_pipeline_medium: 'Газопровод СД',
  gas_pipeline_low: 'Газопровод НД',
  oil_pipeline: 'Нефтепровод',
  water_pipeline: 'Водопровод',
  industrial_building: 'Здание',
  road: 'Дорога',
  other: 'Прочее',
}

const DOC_TYPE_RU = {
  ojr: 'ОЖР',
  welding_journal: 'Журн. сварки',
  isolation_journal: 'Журн. изоляции',
  geodesy_journal: 'Геодезия',
  aosr: 'АОСР',
  hydraulic_test: 'Гидроисп.',
  tightness_test: 'Герметичность',
  purge_act: 'Продувка',
  ks2: 'КС-2',
  ks3: 'КС-3',
  ks11: 'КС-11',
  ppr: 'ППР',
  tech_card: 'Техкарта',
  other: 'Прочее',
}

const PIE_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#6366f1',
]

function StatCard({ icon: Icon, label, value, sub, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    purple: 'bg-purple-50 text-purple-700',
  }
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 flex items-start gap-4">
      <div className={`p-3 rounded-lg ${colors[color]}`}>
        <Icon size={22} />
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-800">{value ?? '—'}</div>
        <div className="text-sm font-medium text-slate-700 mt-0.5">{label}</div>
        {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function SectionTitle({ children }) {
  return <h2 className="text-base font-semibold text-slate-700 mb-3">{children}</h2>
}

function ChartCard({ title, children, className = '' }) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 p-5 ${className}`}>
      <SectionTitle>{title}</SectionTitle>
      {children}
    </div>
  )
}

export default function Statistics() {
  const { data, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => statsApi.get().then(r => r.data),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        Загрузка статистики...
      </div>
    )
  }

  const projects = data?.projects || {}
  const documents = data?.documents || {}
  const reports = data?.shift_reports || {}

  // Проекты по статусу → pie
  const projStatusData = Object.entries(projects.by_status || {})
    .map(([k, v]) => ({ name: STATUS_RU[k] || k, value: v }))

  // Проекты по типу → bar
  const projTypeData = Object.entries(projects.by_type || {})
    .map(([k, v]) => ({ name: TYPE_RU[k] || k, value: v }))

  // Документы по типу → bar (топ 10)
  const docTypeData = Object.entries(documents.by_type || {})
    .map(([k, v]) => ({ name: DOC_TYPE_RU[k] || k, value: v }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10)

  // Рапорты по месяцам → bar
  const monthlyData = (reports.by_month || []).map(r => ({
    name: r.month ? r.month.slice(5) + '.' + r.month.slice(0, 4) : '',
    count: r.count,
  }))

  const docsSignedPct = documents.total
    ? Math.round((documents.signed / documents.total) * 100)
    : 0
  const reportsFinPct = reports.total
    ? Math.round((reports.finalized / reports.total) * 100)
    : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <BarChart2 size={22} className="text-blue-600" />
        <h1 className="text-xl font-bold text-slate-800">Статистика</h1>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={FolderOpen}   label="Проектов"        value={projects.total}  sub={`${projects.active || 0} активных`}  color="blue" />
        <StatCard icon={FileText}     label="Документов"      value={documents.total} sub={`${docsSignedPct}% подписано`}        color="green" />
        <StatCard icon={ClipboardList} label="Сменных рапортов" value={reports.total}  sub={`${reportsFinPct}% финализировано`}  color="amber" />
        <StatCard icon={BarChart2}    label="Финализировано"  value={reports.finalized} sub="рапортов закрыто"                   color="purple" />
      </div>

      {/* Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard title="Проекты по статусу">
          {projStatusData.length ? (
            <ResponsiveContainer width="100%" height={230}>
              <PieChart>
                <Pie data={projStatusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={85} label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                  {projStatusData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </ChartCard>

        <ChartCard title="Проекты по типу">
          {projTypeData.length ? (
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={projTypeData} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </ChartCard>
      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard title="Документы по типу (топ 10)">
          {docTypeData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={docTypeData} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#10b981" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </ChartCard>

        <ChartCard title="Сменные рапорты по месяцам">
          {monthlyData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" name="Рапортов" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </ChartCard>
      </div>

      {/* Doc status progress bars */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <SectionTitle>Статус документооборота</SectionTitle>
        <div className="space-y-3">
          <ProgressBar label="Подписано / Утверждено" value={documents.signed} total={documents.total} color="bg-emerald-500" />
          <ProgressBar label="Черновики" value={documents.draft} total={documents.total} color="bg-amber-400" />
          <ProgressBar label="Финализированных рапортов" value={reports.finalized} total={reports.total} color="bg-blue-500" />
        </div>
      </div>
    </div>
  )
}

function ProgressBar({ label, value = 0, total = 0, color }) {
  const pct = total ? Math.round((value / total) * 100) : 0
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-600">{label}</span>
        <span className="text-slate-500 font-medium">{value} / {total} &nbsp;<span className="text-slate-400">({pct}%)</span></span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Empty() {
  return <div className="text-center text-sm text-slate-400 py-8">Нет данных</div>
}

import { useQuery } from '@tanstack/react-query'
import { projectsApi, agentsApi } from '../utils/api'
import { FolderOpen, FileText, Users, CheckCircle, Clock, AlertTriangle, Building2 } from 'lucide-react'

const STATUS_LABELS = {
  initiation: 'Инициация',
  design: 'Проектирование',
  permits: 'Согласования',
  procurement: 'Закупки',
  construction: 'Строительство',
  testing: 'Испытания',
  commissioning: 'Пуско-наладка',
  acceptance: 'Приемка',
  completed: 'Завершен',
  suspended: 'Приостановлен',
}

const STATUS_COLORS = {
  initiation: 'bg-slate-100 text-slate-700',
  design: 'bg-blue-100 text-blue-700',
  permits: 'bg-yellow-100 text-yellow-700',
  procurement: 'bg-orange-100 text-orange-700',
  construction: 'bg-emerald-100 text-emerald-700',
  testing: 'bg-purple-100 text-purple-700',
  commissioning: 'bg-indigo-100 text-indigo-700',
  acceptance: 'bg-teal-100 text-teal-700',
  completed: 'bg-green-100 text-green-700',
  suspended: 'bg-red-100 text-red-700',
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon size={22} />
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-800">{value}</div>
        <div className="text-sm text-slate-500">{label}</div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(r => r.data),
  })

  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentsApi.list().then(r => r.data),
  })

  const activeProjects = projects.filter(p =>
    !['completed', 'suspended'].includes(p.status)
  ).length

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Дашборд</h2>
        <p className="text-slate-500 mt-1">
          Система автоматизации сопровождения строительных проектов РК
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FolderOpen}
          label="Всего проектов"
          value={projects.length}
          color="bg-blue-50 text-blue-600"
        />
        <StatCard
          icon={Building2}
          label="Активных проектов"
          value={activeProjects}
          color="bg-emerald-50 text-emerald-600"
        />
        <StatCard
          icon={Users}
          label="Агентов-сотрудников"
          value={agents.length}
          color="bg-purple-50 text-purple-600"
        />
        <StatCard
          icon={CheckCircle}
          label="Завершено проектов"
          value={projects.filter(p => p.status === 'completed').length}
          color="bg-green-50 text-green-600"
        />
      </div>

      {/* Projects table */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Активные проекты</h3>
          <a href="/projects" className="text-sm text-blue-600 hover:underline">
            Все проекты →
          </a>
        </div>

        {projects.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <FolderOpen size={48} className="mx-auto mb-3 opacity-30" />
            <p>Нет проектов. Создайте первый проект.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {projects.slice(0, 5).map(project => (
              <a
                key={project.id}
                href={`/projects/${project.id}`}
                className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50 transition-colors"
              >
                <div className="flex-1">
                  <div className="font-medium text-slate-800">{project.name}</div>
                  <div className="text-sm text-slate-500">
                    Шифр: {project.code} · {project.region || 'Регион не указан'}
                  </div>
                </div>
                <div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLORS[project.status] || 'bg-slate-100 text-slate-600'}`}>
                    {STATUS_LABELS[project.status] || project.status}
                  </span>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Agents team preview */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Команда агентов</h3>
          <a href="/agents" className="text-sm text-blue-600 hover:underline">
            Все агенты →
          </a>
        </div>
        <div className="p-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {agents.slice(0, 8).map(agent => (
            <a
              key={agent.role}
              href={`/agents/${agent.role}/chat`}
              className="flex flex-col items-center gap-2 p-4 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50 transition-colors text-center"
            >
              <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
                {agent.avatar_initials}
              </div>
              <div>
                <div className="text-sm font-medium text-slate-800 leading-tight">
                  {agent.name_ru.split(' ').slice(0, 2).join(' ')}
                </div>
                <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                  {agent.position.split('/')[0].trim()}
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}

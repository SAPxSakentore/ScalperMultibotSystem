import { useQuery } from '@tanstack/react-query'
import { agentsApi } from '../utils/api'
import { MessageSquare, Briefcase } from 'lucide-react'

const ROLE_COLORS = {
  ceo: 'bg-purple-600',
  project_manager: 'bg-blue-600',
  chief_engineer: 'bg-indigo-600',
  documentation_manager: 'bg-teal-600',
  quality_control: 'bg-green-600',
  hse_officer: 'bg-orange-500',
  estimator: 'bg-yellow-600',
  legal_compliance: 'bg-red-600',
  field_inspector: 'bg-slate-600',
}

export default function Agents() {
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentsApi.list().then(r => r.data),
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Команда агентов</h2>
        <p className="text-slate-500 mt-1">
          Виртуальные сотрудники компании KazBuildOS — AI-агенты на базе Claude
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-slate-400">Загрузка...</div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map(agent => (
            <div key={agent.role} className="bg-white rounded-xl border border-slate-200 p-5">
              {/* Header */}
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-14 h-14 rounded-full ${ROLE_COLORS[agent.role] || 'bg-slate-600'} flex items-center justify-center text-white font-bold text-xl`}>
                  {agent.avatar_initials}
                </div>
                <div>
                  <div className="font-semibold text-slate-800">{agent.name_ru}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{agent.position}</div>
                </div>
              </div>

              {/* Capabilities */}
              <div className="space-y-1 mb-4">
                {agent.capabilities?.slice(0, 4).map((cap, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-slate-600">
                    <span className="text-emerald-500 mt-0.5">✓</span>
                    <span>{cap}</span>
                  </div>
                ))}
                {agent.capabilities?.length > 4 && (
                  <div className="text-xs text-slate-400">
                    +{agent.capabilities.length - 4} ещё...
                  </div>
                )}
              </div>

              {/* Chat button */}
              <a
                href={`/agents/${agent.role}/chat`}
                className="flex items-center justify-center gap-2 w-full bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg py-2 text-sm font-medium transition-colors"
              >
                <MessageSquare size={15} />
                Задать вопрос
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Таблица прогресса строительства по фазам.
 * Показывает: фаза → выполнено м / км → % от общей длины → полоса прогресса.
 */
import { useQuery } from '@tanstack/react-query'
import { projectsApi } from '../utils/api'
import { Loader2, TrendingUp, AlertCircle } from 'lucide-react'

// Цвет полосы прогресса в зависимости от %
function barColor(pct) {
  if (pct === null) return 'bg-slate-200'
  if (pct >= 100) return 'bg-green-500'
  if (pct >= 60)  return 'bg-blue-500'
  if (pct >= 20)  return 'bg-amber-400'
  return 'bg-orange-400'
}

function textColor(pct) {
  if (pct === null) return 'text-slate-400'
  if (pct >= 100) return 'text-green-700'
  if (pct >= 60)  return 'text-blue-700'
  if (pct >= 20)  return 'text-amber-700'
  return 'text-orange-600'
}

export default function TraceProgress({ projectId, compact = false }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['progress', projectId],
    queryFn: () => projectsApi.getProgress(projectId).then(r => r.data),
    enabled: !!projectId,
    refetchInterval: 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-400 py-6 justify-center">
        <Loader2 size={18} className="animate-spin" />
        <span className="text-sm">Загрузка прогресса...</span>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex items-center gap-2 text-red-400 py-4 text-sm">
        <AlertCircle size={16} /> Не удалось загрузить прогресс
      </div>
    )
  }

  // Только фазы с данными (если compact) или все
  const phases = compact
    ? data.phases.filter(p => p.has_data)
    : data.phases

  const noData = data.phases.every(p => !p.has_data)

  return (
    <div className="space-y-4">
      {/* Итоговая строка */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <TrendingUp size={18} className="text-blue-500" />
          <span className="font-semibold text-slate-800">Прогресс по трассе</span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          {data.total_length_km && (
            <span className="text-slate-500">
              Общая длина: <strong className="text-slate-800">{data.total_length_km} км</strong>
            </span>
          )}
          <span className="text-slate-500">
            Выполнено: <strong className="text-blue-700">{data.overall_done_km} км</strong>
          </span>
          {data.overall_pct !== null && (
            <span className={`font-bold text-base ${textColor(data.overall_pct)}`}>
              {data.overall_pct}%
            </span>
          )}
        </div>
      </div>

      {/* Общая полоса */}
      {data.overall_pct !== null && (
        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${barColor(data.overall_pct)}`}
            style={{ width: `${Math.min(data.overall_pct, 100)}%` }}
          />
        </div>
      )}

      {/* Предупреждение если нет рапортов */}
      {noData && (
        <p className="text-sm text-slate-400 text-center py-2">
          Нет данных — создайте сменные рапорты с указанием метров выполненных работ
        </p>
      )}

      {/* Таблица по фазам */}
      {phases.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-400 uppercase tracking-wide border-b border-slate-100">
                <th className="text-left py-2 pr-4 font-medium w-8">#</th>
                <th className="text-left py-2 pr-4 font-medium">Фаза</th>
                <th className="text-right py-2 pr-4 font-medium whitespace-nowrap">Смен</th>
                <th className="text-right py-2 pr-4 font-medium whitespace-nowrap">Выполнено</th>
                {!compact && (
                  <th className="text-right py-2 pr-4 font-medium whitespace-nowrap">Последний рапорт</th>
                )}
                <th className="text-right py-2 pr-4 font-medium w-16">%</th>
                <th className="py-2 w-32"></th>
              </tr>
            </thead>
            <tbody>
              {phases.map((p, idx) => {
                const pct = p.pct_of_total
                const realIdx = data.phases.indexOf(p)
                return (
                  <tr
                    key={p.phase}
                    className={`border-b border-slate-50 ${p.has_data ? '' : 'opacity-40'}`}
                  >
                    <td className="py-2.5 pr-4 text-slate-400 text-xs">{realIdx + 1}</td>
                    <td className="py-2.5 pr-4 text-slate-700 font-medium leading-tight">
                      {p.name_ru}
                    </td>
                    <td className="py-2.5 pr-4 text-right text-slate-600">
                      {p.has_data ? (
                        <span>
                          {p.shifts_count}
                          {p.finalized_count > 0 && (
                            <span className="text-xs text-green-600 ml-1">
                              ({p.finalized_count} ✓)
                            </span>
                          )}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="py-2.5 pr-4 text-right">
                      {p.has_data ? (
                        <span className="text-slate-800 font-medium">
                          {p.length_done_m >= 1000
                            ? `${p.length_done_km} км`
                            : `${Math.round(p.length_done_m)} м`}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    {!compact && (
                      <td className="py-2.5 pr-4 text-right text-xs text-slate-400">
                        {p.last_date
                          ? new Date(p.last_date).toLocaleDateString('ru-RU')
                          : '—'}
                      </td>
                    )}
                    <td className={`py-2.5 pr-4 text-right font-semibold ${textColor(pct)}`}>
                      {pct !== null ? `${pct}%` : '—'}
                    </td>
                    <td className="py-2.5">
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden w-28">
                        {pct !== null && (
                          <div
                            className={`h-full rounded-full ${barColor(pct)}`}
                            style={{ width: `${Math.min(pct, 100)}%` }}
                          />
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

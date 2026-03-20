import { useQuery } from '@tanstack/react-query'
import { normativesApi } from '../utils/api'
import { BookOpen, Shield, FileCheck } from 'lucide-react'

const CATEGORY_COLORS = {
  'СП РК': 'bg-blue-50 text-blue-700 border-blue-200',
  'СНиП РК': 'bg-indigo-50 text-indigo-700 border-indigo-200',
  'ГОСТ': 'bg-green-50 text-green-700 border-green-200',
  'РД': 'bg-orange-50 text-orange-700 border-orange-200',
  'Закон': 'bg-red-50 text-red-700 border-red-200',
}

export default function Normatives() {
  const { data: normatives = [], isLoading } = useQuery({
    queryKey: ['normatives'],
    queryFn: () => normativesApi.list().then(r => r.data),
  })

  const grouped = normatives.reduce((acc, doc) => {
    if (!acc[doc.category]) acc[doc.category] = []
    acc[doc.category].push(doc)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Нормативная база РК</h2>
        <p className="text-slate-500 mt-1">
          Строительные правила, нормативы и законы Республики Казахстан
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-slate-400">Загрузка...</div>
      ) : (
        Object.entries(grouped).map(([category, docs]) => (
          <div key={category} className="bg-white rounded-xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
              <BookOpen size={18} className="text-slate-400" />
              <h3 className="font-semibold text-slate-800">{category}</h3>
              <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">
                {docs.length} документов
              </span>
            </div>
            <div className="divide-y divide-slate-50">
              {docs.map((doc, i) => (
                <div key={i} className="px-6 py-4">
                  <div className="flex items-start gap-3">
                    <span className={`text-xs font-medium px-2 py-1 rounded border shrink-0 ${CATEGORY_COLORS[doc.category] || 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                      {doc.code}
                    </span>
                    <div>
                      <div className="font-medium text-slate-800 text-sm">{doc.title}</div>
                      <div className="text-xs text-slate-500 mt-1">
                        Применяется: {doc.applies_to.join(', ')}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

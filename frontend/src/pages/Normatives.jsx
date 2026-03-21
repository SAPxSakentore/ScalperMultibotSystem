import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { normativesApi } from '../utils/api'
import { BookOpen, Search, X } from 'lucide-react'

const CATEGORY_COLORS = {
  'СП РК': 'bg-blue-50 text-blue-700 border-blue-200',
  'СНиП РК': 'bg-indigo-50 text-indigo-700 border-indigo-200',
  'ГОСТ': 'bg-green-50 text-green-700 border-green-200',
  'РД': 'bg-orange-50 text-orange-700 border-orange-200',
  'Закон': 'bg-red-50 text-red-700 border-red-200',
}

export default function Normatives() {
  const [query, setQuery] = useState('')
  const [filterCat, setFilterCat] = useState('')

  const { data: normatives = [], isLoading } = useQuery({
    queryKey: ['normatives'],
    queryFn: () => normativesApi.list().then(r => r.data),
  })

  const categories = useMemo(() => [...new Set(normatives.map(d => d.category))], [normatives])

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return normatives.filter(d => {
      const matchCat = !filterCat || d.category === filterCat
      const matchQ = !q || d.code.toLowerCase().includes(q) || d.title.toLowerCase().includes(q) || d.applies_to.some(a => a.toLowerCase().includes(q))
      return matchCat && matchQ
    })
  }, [normatives, query, filterCat])

  const grouped = useMemo(() => filtered.reduce((acc, doc) => {
    if (!acc[doc.category]) acc[doc.category] = []
    acc[doc.category].push(doc)
    return acc
  }, {}), [filtered])

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Нормативная база РК</h2>
        <p className="text-slate-500 mt-1">Строительные правила, нормативы и законы Республики Казахстан</p>
      </div>

      {/* Фильтры */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Поиск по шифру, названию, области применения..."
            className="w-full border border-slate-200 rounded-xl pl-9 pr-9 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          {query && (
            <button onClick={() => setQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X size={14} />
            </button>
          )}
        </div>
        <select
          value={filterCat}
          onChange={e => setFilterCat(e.target.value)}
          className="border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
        >
          <option value="">Все категории</option>
          {categories.map(c => <option key={c}>{c}</option>)}
        </select>
        {(query || filterCat) && (
          <span className="self-center text-sm text-slate-500">{filtered.length} документов</span>
        )}
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-slate-400">Загрузка...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-400">Ничего не найдено</div>
      ) : (
        Object.entries(grouped).map(([category, docs]) => (
          <div key={category} className="bg-white rounded-xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
              <BookOpen size={18} className="text-slate-400" />
              <h3 className="font-semibold text-slate-800">{category}</h3>
              <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{docs.length}</span>
            </div>
            <div className="divide-y divide-slate-50">
              {docs.map((doc, i) => (
                <div key={i} className="px-6 py-3.5">
                  <div className="flex items-start gap-3">
                    <span className={`text-xs font-medium px-2 py-1 rounded border shrink-0 ${CATEGORY_COLORS[doc.category] || 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                      {doc.code}
                    </span>
                    <div>
                      <div className="font-medium text-slate-800 text-sm">{doc.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {doc.applies_to.join(' · ')}
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

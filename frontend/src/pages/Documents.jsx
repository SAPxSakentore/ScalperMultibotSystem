import { FileText, BookOpen } from 'lucide-react'

export default function Documents() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Документы</h2>
        <p className="text-slate-500 mt-1">
          Исполнительно-техническая документация всех проектов
        </p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400">
        <FileText size={48} className="mx-auto mb-3 opacity-30" />
        <p>Выберите проект для просмотра документации</p>
        <a href="/projects" className="text-blue-600 text-sm mt-2 inline-block hover:underline">
          Перейти к проектам →
        </a>
      </div>
    </div>
  )
}

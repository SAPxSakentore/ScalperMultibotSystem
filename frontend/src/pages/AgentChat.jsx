import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { agentsApi } from '../utils/api'
import { Send, Loader2, ArrowLeft, Trash2, History } from 'lucide-react'

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

const MAX_HISTORY = 100  // максимум сообщений в localStorage

function storageKey(role) {
  return `agent_chat_${role}`
}

function loadHistory(role) {
  try {
    const raw = localStorage.getItem(storageKey(role))
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(role, messages) {
  try {
    const trimmed = messages.slice(-MAX_HISTORY)
    localStorage.setItem(storageKey(role), JSON.stringify(trimmed))
  } catch { /* ignore storage errors */ }
}

export default function AgentChat() {
  const { role } = useParams()
  const [messages, setMessages] = useState(() => loadHistory(role))
  const [input, setInput] = useState('')
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const messagesEndRef = useRef(null)

  const { data: agent } = useQuery({
    queryKey: ['agent', role],
    queryFn: () => agentsApi.get(role).then(r => r.data),
  })

  // Сохраняем историю при каждом изменении
  useEffect(() => {
    saveHistory(role, messages)
  }, [role, messages])

  // Скролл вниз при новых сообщениях
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addMessage = useCallback((msg) => {
    setMessages(prev => [...prev, {
      ...msg,
      timestamp: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      date: new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
    }])
  }, [])

  const chatMutation = useMutation({
    mutationFn: (message) => agentsApi.chat(role, { message }),
    onSuccess: (data) => {
      addMessage({ role: 'agent', text: data.data.response })
    },
    onError: () => {
      addMessage({ role: 'agent', text: '⚠️ Ошибка соединения с агентом. Проверьте наличие ANTHROPIC_API_KEY.' })
    },
  })

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim() || chatMutation.isPending) return
    const userMessage = input.trim()
    setInput('')
    addMessage({ role: 'user', text: userMessage })
    chatMutation.mutate(userMessage)
  }

  const clearHistory = () => {
    setMessages([])
    localStorage.removeItem(storageKey(role))
    setShowClearConfirm(false)
  }

  if (!agent) return <div className="text-center py-12 text-slate-400">Загрузка...</div>

  // Группируем сообщения по дате для разделителей
  let lastDate = null

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4 flex items-center gap-4">
        <a href="/agents" className="text-slate-400 hover:text-slate-600">
          <ArrowLeft size={20} />
        </a>
        <div className={`w-12 h-12 rounded-full ${ROLE_COLORS[role] || 'bg-slate-600'} flex items-center justify-center text-white font-bold`}>
          {agent.avatar_initials}
        </div>
        <div className="flex-1">
          <div className="font-semibold text-slate-800">{agent.name_ru}</div>
          <div className="text-sm text-slate-500">{agent.position}</div>
        </div>
        <div className="flex items-center gap-3">
          {messages.length > 0 && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <History size={12} />
              {messages.length} сообщ.
            </div>
          )}
          <div className="flex items-center gap-1 text-xs text-emerald-600">
            <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
            Онлайн
          </div>
          {messages.length > 0 && !showClearConfirm && (
            <button
              onClick={() => setShowClearConfirm(true)}
              title="Очистить историю"
              className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Trash2 size={15} />
            </button>
          )}
          {showClearConfirm && (
            <div className="flex items-center gap-2 bg-red-50 rounded-lg px-2 py-1">
              <span className="text-xs text-red-600">Очистить?</span>
              <button onClick={clearHistory} className="text-xs font-medium text-red-700 hover:underline">Да</button>
              <button onClick={() => setShowClearConfirm(false)} className="text-xs text-slate-500 hover:underline">Нет</button>
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 bg-white rounded-xl border border-slate-200 p-4 overflow-y-auto mb-4 space-y-3 scrollbar-thin">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 py-8">
            <div className={`w-16 h-16 rounded-full ${ROLE_COLORS[role] || 'bg-slate-600'} flex items-center justify-center text-white font-bold text-2xl mx-auto mb-3`}>
              {agent.avatar_initials}
            </div>
            <p className="font-medium">{agent.name_ru}</p>
            <p className="text-sm mt-1">{agent.position}</p>
            <p className="text-sm mt-4 text-slate-500">
              Задайте вопрос по строительству, нормативам РК или документации
            </p>
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {(agent.capabilities || []).slice(0, 3).map(cap => (
                <button
                  key={cap}
                  onClick={() => { setInput(cap); }}
                  className="text-xs bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-600 px-3 py-1.5 rounded-full transition-colors"
                >
                  {cap}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          const showDate = msg.date && msg.date !== lastDate
          lastDate = msg.date
          return (
            <div key={i}>
              {showDate && (
                <div className="flex items-center gap-2 my-3">
                  <div className="flex-1 h-px bg-slate-100" />
                  <span className="text-xs text-slate-400">{msg.date}</span>
                  <div className="flex-1 h-px bg-slate-100" />
                </div>
              )}
              <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`
                  max-w-[80%] rounded-2xl px-4 py-3 text-sm
                  ${msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-sm'
                    : 'bg-slate-100 text-slate-800 rounded-tl-sm'
                  }
                `}>
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.text}</div>
                  <div className={`text-xs mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-slate-400'}`}>
                    {msg.timestamp}
                  </div>
                </div>
              </div>
            </div>
          )
        })}

        {chatMutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3">
              <Loader2 size={16} className="animate-spin text-slate-400" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="flex gap-3">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Задайте вопрос агенту..."
          className="flex-1 border border-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={!input.trim() || chatMutation.isPending}
          className="bg-blue-600 text-white px-4 py-3 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  )
}

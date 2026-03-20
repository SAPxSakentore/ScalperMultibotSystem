import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { agentsApi } from '../utils/api'
import { Send, Loader2, ArrowLeft } from 'lucide-react'

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

export default function AgentChat() {
  const { role } = useParams()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)

  const { data: agent } = useQuery({
    queryKey: ['agent', role],
    queryFn: () => agentsApi.get(role).then(r => r.data),
  })

  const chatMutation = useMutation({
    mutationFn: (message) => agentsApi.chat(role, { message }),
    onSuccess: (data) => {
      setMessages(prev => [...prev, {
        role: 'agent',
        text: data.data.response,
        timestamp: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      }])
    },
    onError: () => {
      setMessages(prev => [...prev, {
        role: 'agent',
        text: '⚠️ Ошибка соединения с агентом. Проверьте наличие ANTHROPIC_API_KEY.',
        timestamp: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      }])
    }
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim() || chatMutation.isPending) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, {
      role: 'user',
      text: userMessage,
      timestamp: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
    }])
    chatMutation.mutate(userMessage)
  }

  if (!agent) return <div className="text-center py-12 text-slate-400">Загрузка...</div>

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
        <div>
          <div className="font-semibold text-slate-800">{agent.name_ru}</div>
          <div className="text-sm text-slate-500">{agent.position}</div>
        </div>
        <div className="ml-auto flex items-center gap-1 text-xs text-emerald-600">
          <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
          Онлайн
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 bg-white rounded-xl border border-slate-200 p-4 overflow-y-auto mb-4 space-y-4 scrollbar-thin">
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
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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
        ))}

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

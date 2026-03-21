/**
 * SmetaTab — вкладка «Смета» в карточке проекта.
 *
 * Возможности:
 *  - CRUD сметных позиций (наименование, ед. изм., расценка, плановый объём)
 *  - Диалог «Акты за период» — агрегация объёмов из рапортов + генерация КС-2/КС-3
 */
import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { smetaApi } from '../utils/api'
import {
  Plus, Trash2, Pencil, Check, X, FileDown, Loader2,
  Calculator, BarChart2, Calendar, AlertCircle, ChevronDown, ChevronUp,
  TrendingUp,
} from 'lucide-react'

// ── Форматирование ────────────────────────────────────────────────────────────
const fmt = (n, digits = 2) =>
  typeof n === 'number' ? n.toLocaleString('ru-RU', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—'

const STATUS_COLOR = (pct) => {
  if (pct >= 100) return 'bg-emerald-500'
  if (pct >= 60)  return 'bg-blue-500'
  if (pct >= 20)  return 'bg-amber-400'
  return 'bg-slate-300'
}

// ── Компонент строки ──────────────────────────────────────────────────────────
function SmetaRow({ item, onEdit, onDelete }) {
  return (
    <tr className="hover:bg-slate-50 border-b border-slate-100">
      <td className="px-3 py-2 text-center text-xs text-slate-500">{item.position_no}</td>
      <td className="px-3 py-2 text-xs text-slate-400 whitespace-nowrap">{item.section}</td>
      <td className="px-3 py-2 text-sm text-slate-800">{item.name}</td>
      <td className="px-3 py-2 text-xs text-slate-500 text-center">{item.unit}</td>
      <td className="px-3 py-2 text-xs text-right tabular-nums">{fmt(item.planned_qty, 2)}</td>
      <td className="px-3 py-2 text-xs text-right tabular-nums">{fmt(item.unit_price)}</td>
      <td className="px-3 py-2 text-xs text-right tabular-nums font-medium">{fmt(item.planned_amount)}</td>
      <td className="px-2 py-2 text-xs text-slate-400">{item.normative_code}</td>
      <td className="px-2 py-2 whitespace-nowrap">
        <button onClick={() => onEdit(item)} className="p-1 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded"><Pencil size={13} /></button>
        <button onClick={() => onDelete(item.id)} className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"><Trash2 size={13} /></button>
      </td>
    </tr>
  )
}

// ── Форма редактирования / создания ──────────────────────────────────────────
function ItemForm({ initial, onSave, onCancel, saving }) {
  const [f, setF] = useState({
    position_no: initial?.position_no ?? 1,
    section: initial?.section ?? '',
    name: initial?.name ?? '',
    work_type_key: initial?.work_type_key ?? '',
    unit: initial?.unit ?? 'м',
    unit_price: initial?.unit_price ?? 0,
    planned_qty: initial?.planned_qty ?? 0,
    normative_code: initial?.normative_code ?? '',
    notes: initial?.notes ?? '',
  })
  const set = (k) => (e) => setF(p => ({ ...p, [k]: e.target.value }))
  const setN = (k) => (e) => setF(p => ({ ...p, [k]: parseFloat(e.target.value) || 0 }))

  return (
    <tr className="bg-blue-50">
      <td className="px-2 py-1"><input type="number" value={f.position_no} onChange={setN('position_no')} className="w-12 border rounded px-1 py-0.5 text-xs" /></td>
      <td className="px-2 py-1"><input value={f.section} onChange={set('section')} placeholder="Раздел" className="w-24 border rounded px-1 py-0.5 text-xs" /></td>
      <td className="px-2 py-1">
        <input value={f.name} onChange={set('name')} placeholder="Наименование работ *" className="w-full border rounded px-2 py-1 text-sm" required />
        <input value={f.work_type_key} onChange={set('work_type_key')} placeholder="Ключ матчинга (из рапортов)" className="w-full border rounded px-1 py-0.5 text-xs mt-1 text-slate-500" />
      </td>
      <td className="px-2 py-1"><input value={f.unit} onChange={set('unit')} className="w-12 border rounded px-1 py-0.5 text-xs" /></td>
      <td className="px-2 py-1"><input type="number" step="0.01" value={f.planned_qty} onChange={setN('planned_qty')} className="w-20 border rounded px-1 py-0.5 text-xs" /></td>
      <td className="px-2 py-1"><input type="number" step="0.01" value={f.unit_price} onChange={setN('unit_price')} className="w-24 border rounded px-1 py-0.5 text-xs" /></td>
      <td className="px-2 py-1 text-xs tabular-nums">{fmt(f.planned_qty * f.unit_price)}</td>
      <td className="px-2 py-1"><input value={f.normative_code} onChange={set('normative_code')} placeholder="ТЕР..." className="w-20 border rounded px-1 py-0.5 text-xs" /></td>
      <td className="px-2 py-1 whitespace-nowrap">
        <button onClick={() => onSave(f)} disabled={!f.name || saving} className="p-1 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50">
          {saving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
        </button>
        <button onClick={onCancel} className="p-1 ml-1 border rounded hover:bg-slate-100"><X size={13} /></button>
      </td>
    </tr>
  )
}

// ── Диалог «Акты за период» ───────────────────────────────────────────────────
function ActsDialog({ projectId, smetaItems, onClose }) {
  const today = new Date().toISOString().slice(0, 10)
  const monthStart = today.slice(0, 8) + '01'

  const [dateFrom, setDateFrom] = useState(monthStart)
  const [dateTo, setDateTo] = useState(today)
  const [contractNo, setContractNo] = useState('')
  const [actNo, setActNo] = useState('')
  const [includeZero, setIncludeZero] = useState(false)
  const [output, setOutput] = useState('zip')

  const [previewOpen, setPreviewOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  const { data: volumes, isLoading: loadingVol, refetch } = useQuery({
    queryKey: ['work-volumes', projectId, dateFrom, dateTo],
    queryFn: () => smetaApi.workVolumes(projectId, dateFrom, dateTo).then(r => r.data),
    enabled: previewOpen,
  })

  const totalPeriod = useMemo(() =>
    (volumes || []).reduce((s, r) => s + r.actual_amount, 0), [volumes])

  const handleGenerate = async () => {
    setGenerating(true)
    setError('')
    try {
      const label = `${dateFrom} — ${dateTo}`
      const resp = await smetaApi.generateActs(projectId, {
        date_from: dateFrom,
        date_to: dateTo,
        period_label: label,
        contract_number: contractNo || undefined,
        act_number: actNo || undefined,
        include_zero_rows: includeZero,
        output,
      })
      const blob = new Blob([resp.data], {
        type: output === 'zip'
          ? 'application/zip'
          : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const ext = output === 'zip' ? 'zip' : 'docx'
      a.href = url
      a.download = `Acts_${label}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError('Ошибка генерации: ' + (e.response?.data?.detail || e.message))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <Calculator size={20} className="text-blue-600" />
            <h2 className="text-lg font-bold text-slate-800">Акты выполненных работ за период</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg"><X size={18} /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Period */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">Начало периода *</label>
              <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">Конец периода *</label>
              <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">№ договора</label>
              <input value={contractNo} onChange={e => setContractNo(e.target.value)}
                placeholder="Договор №___" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">№ акта</label>
              <input value={actNo} onChange={e => setActNo(e.target.value)}
                placeholder="КС2-2026-01" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>

          {/* Options */}
          <div className="flex items-center gap-6 text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={includeZero} onChange={e => setIncludeZero(e.target.checked)} className="rounded" />
              <span className="text-slate-600">Включать позиции с нулевым объёмом</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Скачать:</span>
              {[['zip', 'ZIP + Excel'], ['ks2', 'КС-2 (DOCX)'], ['ks3', 'КС-3 (DOCX)'], ['xlsx', 'КС-2+3 Excel']].map(([v, l]) => (
                <label key={v} className="flex items-center gap-1 cursor-pointer">
                  <input type="radio" name="output" value={v} checked={output === v} onChange={() => setOutput(v)} />
                  <span className={output === v ? 'text-blue-700 font-medium' : 'text-slate-600'}>{l}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Preview toggle */}
          <div>
            <button
              onClick={() => { setPreviewOpen(p => !p); if (!previewOpen) refetch() }}
              className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              {previewOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
              {previewOpen ? 'Скрыть предпросмотр объёмов' : 'Показать объёмы из рапортов за период'}
            </button>
          </div>

          {previewOpen && (
            <div>
              {loadingVol ? (
                <div className="text-center py-6 text-slate-400"><Loader2 size={20} className="animate-spin mx-auto" /></div>
              ) : !volumes?.length ? (
                <div className="text-center py-6 text-slate-400 bg-slate-50 rounded-xl">
                  <AlertCircle size={20} className="mx-auto mb-2 opacity-40" />
                  <p>Нет данных за период. Проверьте наличие финализированных рапортов.</p>
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50">
                      <tr>
                        {['№', 'Наименование', 'Ед.', 'Объём по смете', 'Факт за период', 'Нараст. итог', 'Цена, тг.', 'Сумма за период', 'Сумма нараст.', '%'].map(h => (
                          <th key={h} className="px-2 py-2 text-left font-medium text-slate-500 whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(volumes || []).filter(r => includeZero || r.actual_qty > 0).map((r, i) => (
                        <tr key={i} className={`border-t ${r.smeta_id ? '' : 'bg-amber-50'}`}>
                          <td className="px-2 py-1.5 text-slate-500">{r.position_no}</td>
                          <td className="px-2 py-1.5 max-w-[200px] truncate" title={r.name}>
                            {!r.smeta_id && <span className="text-amber-600 text-[10px] mr-1">⚠ вне сметы</span>}
                            {r.name}
                            {r.chainage_list?.length > 0 && (
                              <div className="text-[10px] text-slate-400">{r.chainage_list.slice(0, 2).join('; ')}</div>
                            )}
                          </td>
                          <td className="px-2 py-1.5 text-slate-500">{r.unit}</td>
                          <td className="px-2 py-1.5 tabular-nums text-right">{fmt(r.planned_qty, 1)}</td>
                          <td className="px-2 py-1.5 tabular-nums text-right font-medium text-blue-700">{fmt(r.actual_qty, 2)}</td>
                          <td className="px-2 py-1.5 tabular-nums text-right text-slate-600">{fmt(r.cumulative_qty, 2)}</td>
                          <td className="px-2 py-1.5 tabular-nums text-right">{fmt(r.unit_price)}</td>
                          <td className="px-2 py-1.5 tabular-nums text-right font-medium">{fmt(r.actual_amount)}</td>
                          <td className="px-2 py-1.5 tabular-nums text-right text-slate-600">{fmt(r.cumulative_amount)}</td>
                          <td className="px-2 py-1.5">
                            <div className="flex items-center gap-1 min-w-[60px]">
                              <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full ${STATUS_COLOR(r.completion_pct)}`} style={{ width: `${Math.min(r.completion_pct, 100)}%` }} />
                              </div>
                              <span className="text-[10px] text-slate-500 w-8 text-right">{r.completion_pct}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {/* Итого */}
                      <tr className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
                        <td colSpan={7} className="px-2 py-2 text-right text-sm">ИТОГО за период:</td>
                        <td className="px-2 py-2 tabular-nums text-right text-sm">{fmt(totalPeriod)}</td>
                        <td colSpan={2} className="px-2 py-2 text-xs text-slate-500">
                          НДС 12%: {fmt(totalPeriod * 0.12)}<br />
                          С НДС: {fmt(totalPeriod * 1.12)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
              <AlertCircle size={16} /> {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-slate-50 rounded-b-2xl">
          <div className="text-sm text-slate-500">
            {smetaItems?.length ? `${smetaItems.length} позиций в смете` : 'Смета не заполнена'}
          </div>
          <div className="flex gap-3">
            <button onClick={onClose} className="px-4 py-2 text-sm border rounded-xl hover:bg-slate-100">Закрыть</button>
            <button
              onClick={handleGenerate}
              disabled={generating || !dateFrom || !dateTo}
              className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white text-sm rounded-xl hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              {generating ? <Loader2 size={15} className="animate-spin" /> : <FileDown size={15} />}
              {generating ? 'Генерация...' : 'Сформировать акты'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Мини-дашборд прогресса сметы ─────────────────────────────────────────────
function SmetaProgress({ projectId, items }) {
  const { data: volumes } = useQuery({
    queryKey: ['smeta-progress', projectId],
    queryFn: () => smetaApi.cumulativeProgress(projectId).then(r => r.data),
    enabled: items.length > 0,
  })

  if (!volumes?.length || !items.length) return null

  const totalPlanned  = items.reduce((s, i) => s + i.planned_amount, 0)
  const totalActual   = volumes.filter(v => v.smeta_id).reduce((s, v) => s + v.cumulative_amount, 0)
  const overallPct    = totalPlanned > 0 ? Math.min(Math.round(totalActual / totalPlanned * 100), 100) : 0
  const outsideSmeta  = volumes.filter(v => !v.smeta_id && v.actual_qty > 0).length

  // Разбивка по разделам
  const sections = {}
  items.forEach(i => {
    const sec = i.section || 'Без раздела'
    if (!sections[sec]) sections[sec] = { planned: 0, actual: 0 }
    sections[sec].planned += i.planned_amount
  })
  volumes.filter(v => v.smeta_id).forEach(v => {
    const item = items.find(i => i.id === v.smeta_id)
    if (item) {
      const sec = item.section || 'Без раздела'
      if (sections[sec]) sections[sec].actual = (sections[sec].actual || 0) + v.cumulative_amount
    }
  })

  const topSections = Object.entries(sections)
    .map(([sec, d]) => ({ sec, pct: d.planned > 0 ? Math.round(d.actual / d.planned * 100) : 0, planned: d.planned, actual: d.actual }))
    .sort((a, b) => b.planned - a.planned)
    .slice(0, 5)

  return (
    <div className="bg-gradient-to-r from-blue-50 to-slate-50 rounded-xl border border-blue-100 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <TrendingUp size={15} className="text-blue-600" />
          Прогресс выполнения сметы (с начала года)
        </div>
        <div className="text-2xl font-bold text-blue-700">{overallPct}%</div>
      </div>
      <div className="h-2.5 bg-white rounded-full overflow-hidden border border-blue-100">
        <div
          className={`h-full rounded-full transition-all duration-700 ${overallPct >= 90 ? 'bg-emerald-500' : overallPct >= 60 ? 'bg-blue-500' : overallPct >= 30 ? 'bg-amber-400' : 'bg-orange-400'}`}
          style={{ width: `${overallPct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Выполнено: <span className="font-medium text-slate-700">{fmt(totalActual)} тг.</span></span>
        <span>По смете: <span className="font-medium text-slate-700">{fmt(totalPlanned)} тг.</span></span>
        {outsideSmeta > 0 && <span className="text-amber-600">⚠ {outsideSmeta} внесметных видов работ</span>}
      </div>
      {topSections.length > 1 && (
        <div className="space-y-1.5 pt-1">
          {topSections.map(({ sec, pct, actual, planned }) => (
            <div key={sec} className="flex items-center gap-2">
              <span className="text-xs text-slate-500 w-32 truncate" title={sec}>{sec}</span>
              <div className="flex-1 h-1.5 bg-white rounded-full overflow-hidden border border-slate-100">
                <div className={`h-full rounded-full ${STATUS_COLOR(pct)}`} style={{ width: `${Math.min(pct, 100)}%` }} />
              </div>
              <span className="text-xs text-slate-500 w-8 text-right">{pct}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Основной компонент ────────────────────────────────────────────────────────
export default function SmetaTab({ projectId }) {
  const queryClient = useQueryClient()
  const [editItem, setEditItem] = useState(null)   // null | item | 'new'
  const [showActs, setShowActs] = useState(false)

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['smeta', projectId],
    queryFn: () => smetaApi.list(projectId).then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (data) => smetaApi.create({ project_id: projectId, ...data }),
    onSuccess: () => { queryClient.invalidateQueries(['smeta', projectId]); setEditItem(null) },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => smetaApi.update(id, data),
    onSuccess: () => { queryClient.invalidateQueries(['smeta', projectId]); setEditItem(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => smetaApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries(['smeta', projectId]),
  })

  const totalPlanned = items.reduce((s, i) => s + i.planned_amount, 0)

  if (isLoading) return <div className="text-center py-8 text-slate-400">Загрузка сметы...</div>

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-700">Сметные позиции</h3>
          {items.length > 0 && (
            <div className="text-xs text-slate-500 mt-0.5">
              {items.length} позиций · Сумма по смете: <span className="font-medium text-slate-700">{fmt(totalPlanned)} тг.</span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowActs(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700"
          >
            <BarChart2 size={14} />
            Акты за период
          </button>
          <button
            onClick={() => setEditItem('new')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            <Plus size={14} />
            Добавить позицию
          </button>
        </div>
      </div>

      {/* Прогресс */}
      <SmetaProgress projectId={projectId} items={items} />

      {/* Table */}
      {items.length === 0 && editItem !== 'new' ? (
        <div className="text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-400">
          <Calculator size={32} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">Смета не заполнена</p>
          <p className="text-sm mt-1">Добавьте позиции с расценками для расчёта КС-2 и КС-3</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b">
              <tr>
                {['№', 'Раздел', 'Наименование работ', 'Ед.', 'Объём по смете', 'Расценка, тг.', 'Сумма, тг.', 'Код НТД', ''].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-medium text-slate-500 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                editItem?.id === item.id
                  ? <ItemForm key={item.id} initial={editItem} saving={updateMut.isPending}
                      onSave={(data) => updateMut.mutate({ id: item.id, data })}
                      onCancel={() => setEditItem(null)} />
                  : <SmetaRow key={item.id} item={item}
                      onEdit={setEditItem}
                      onDelete={(id) => { if (confirm('Удалить позицию?')) deleteMut.mutate(id) }} />
              ))}
              {editItem === 'new' && (
                <ItemForm initial={{ position_no: items.length + 1 }} saving={createMut.isPending}
                  onSave={(data) => createMut.mutate(data)}
                  onCancel={() => setEditItem(null)} />
              )}
            </tbody>
            <tfoot className="border-t-2 border-slate-200 bg-slate-50">
              <tr>
                <td colSpan={6} className="px-3 py-2 text-right text-sm font-semibold text-slate-700">ИТОГО по смете:</td>
                <td className="px-3 py-2 text-right text-sm font-bold text-slate-800 tabular-nums">{fmt(totalPlanned)} тг.</td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Акты диалог */}
      {showActs && (
        <ActsDialog
          projectId={projectId}
          smetaItems={items}
          onClose={() => setShowActs(false)}
        />
      )}
    </div>
  )
}

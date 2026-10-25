import { useState } from 'react'

function formatDate(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  } catch {
    return value
  }
}

function Tag({ color, children }) {
  const palette = {
    fact: 'border-blue-500/50 text-blue-400 bg-blue-500/10',
    bank: 'border-green-500/50 text-green-400 bg-green-500/10',
    ai: 'border-purple-500/50 text-purple-400 bg-purple-500/10',
    demo: 'border-amber-500/50 text-amber-400 bg-amber-500/10',
  }
  return (
    <span className={`text-xs border px-2 py-1 rounded ${palette[color] || palette.ai}`}>
      {children}
    </span>
  )
}

export default function NewsCard({ item, onAsk, onToggleFavorite }) {
  const { news, insight } = item
  const [question, setQuestion] = useState('')
  const [chatOpen, setChatOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [asking, setAsking] = useState(false)

  async function handleAsk(e) {
    e.preventDefault()
    if (!question.trim()) return
    const q = question.trim()
    setQuestion('')
    setChatOpen(true)
    setChatHistory((h) => [...h, { role: 'user', text: q }])
    setAsking(true)
    try {
      const result = await onAsk(item.id, q)
      setChatHistory((h) => [...h, { role: 'ai', text: result.answer, demo: result.is_demo }])
    } catch (err) {
      setChatHistory((h) => [...h, { role: 'ai', text: err?.message || 'Ошибка запроса.', demo: true }])
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 mb-6 shadow-lg">
      {/* Шапка карточки */}
      <div className="flex gap-2 text-xs text-slate-400 mb-3 items-center flex-wrap">
        <Tag color="fact">Факт</Tag>
        <span>{news.source}</span>
        <span>•</span>
        <span>{formatDate(news.published_at)}</span>
        <span className="bg-slate-700 text-slate-300 px-2 py-0.5 rounded">{news.category}</span>
        <span className="ml-auto bg-slate-700/60 text-slate-300 px-2 py-0.5 rounded">
          Важность {item.importance_score}/10
        </span>
      </div>

      <h2 className="text-xl font-semibold text-white mb-4">{news.title}</h2>

      {/* Q1 — Что произошло */}
      <p className="text-slate-300 text-sm leading-relaxed mb-5">{news.summary_facts}</p>

      {/* Q2 — Почему важно */}
      <div className="bg-slate-900/60 rounded-lg p-5 mb-4 border border-slate-700/50">
        <h3 className="text-sm font-bold text-purple-400 mb-2">
          Почему это важно для вашей компании
        </h3>
        <p className="text-slate-300 text-sm leading-relaxed">{insight.why_it_matters}</p>

        {/* Q3 — Риски и возможности */}
        {(insight.risks?.length > 0 || insight.opportunities?.length > 0) && (
          <div className="grid sm:grid-cols-2 gap-4 mt-4">
            <div>
              <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wide mb-1.5">
                Риски
              </h4>
              <ul className="space-y-1">
                {insight.risks?.map((risk, i) => (
                  <li key={i} className="text-slate-300 text-sm flex gap-2">
                    <span className="text-red-400">▲</span>
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-green-400 uppercase tracking-wide mb-1.5">
                Возможности
              </h4>
              <ul className="space-y-1">
                {insight.opportunities?.map((opp, i) => (
                  <li key={i} className="text-slate-300 text-sm flex gap-2">
                    <span className="text-green-400">▲</span>
                    {opp}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Q4 — Действия */}
      <div className="bg-slate-900/60 rounded-lg p-5 mb-4 border border-slate-700/50">
        <h3 className="text-sm font-bold text-sky-400 mb-2">Рекомендуемые действия</h3>
        <p className="text-slate-300 text-sm leading-relaxed">{insight.action_item}</p>
      </div>

      {/* Q5 — Позиция банка */}
      <div className="bg-slate-900/60 rounded-lg p-5 mb-4 border border-slate-700/50">
        <h3 className="text-sm font-bold text-green-400 mb-2">Как это оценивает Альфа-Банк</h3>
        {insight.alfa_bank_position ? (
          <>
            <p className="text-slate-300 text-sm leading-relaxed">{insight.alfa_bank_position}</p>
            {(insight.alfa_report_name || insight.alfa_report_page) && (
              <p className="text-slate-500 text-xs mt-2">
                Источник: {insight.alfa_report_name}
                {insight.alfa_report_page ? `, стр. ${insight.alfa_report_page}` : ''}
              </p>
            )}
          </>
        ) : (
          <p className="text-slate-500 text-sm">
            Релевантная позиция банка в корпусе отчётов не найдена (корпус не проиндексирован).
          </p>
        )}
      </div>

      {/* Q6 — Основание вывода и агентная трассировка */}
      <div className="bg-slate-900/60 rounded-lg p-5 mb-4 border border-slate-700/50">
        <h3 className="text-sm font-bold text-slate-200 mb-2">На чём основан вывод</h3>
        {(insight.traceability?.matched_company_features?.length > 0) && (
          <div className="flex flex-wrap gap-2 mb-2">
            {insight.traceability.matched_company_features.map((feature) => (
              <Tag key={feature} color="fact">
                {feature}
              </Tag>
            ))}
          </div>
        )}
        {(insight.traceability?.verified_sources?.length > 0) && (
          <p className="text-slate-500 text-xs mb-2">
            Источники: {insight.traceability.verified_sources.join('; ')}
          </p>
        )}

        {insight.agent_steps?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-700/50">
            <h4 className="text-xs font-semibold text-purple-400 uppercase tracking-wide mb-1.5">
              Шаги агента
            </h4>
            <ol className="space-y-0.5 list-decimal list-inside">
              {insight.agent_steps.map((step, i) => (
                <li key={i} className="text-slate-400 text-xs">
                  {step}
                </li>
              ))}
            </ol>
            {insight.self_check && (
              <p className="text-xs mt-2">
                {insight.self_check.passed ? (
                  <span className="text-green-400">✓ Самопроверка пройдена</span>
                ) : (
                  <span className="text-red-400">✗ Самопроверка: есть нарушения</span>
                )}
                {insight.confidence != null && (
                  <span className="text-slate-500"> · уверенность {Math.round(insight.confidence * 100)}%</span>
                )}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Метки происхождения */}
      <div className="flex flex-wrap gap-2 mb-4">
        <Tag color="fact">[Факт]</Tag>
        <Tag color="bank">[Позиция банка]</Tag>
        <Tag color="ai">[Вывод AI]</Tag>
        {item.is_demo && <Tag color="demo">демо / без LLM</Tag>}
      </div>

      {/* Действия */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={() => setChatOpen((v) => !v)}
          className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer"
        >
          💬 Спросить нейросеть
        </button>
        <button
          onClick={() => onToggleFavorite(item.id, !item.is_favorite)}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
            item.is_favorite
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/50'
              : 'bg-slate-700 hover:bg-slate-600 text-white'
          }`}
        >
          {item.is_favorite ? '★ В избранном' : '☆ В избранное'}
        </button>
      </div>

      {/* Чат */}
      {chatOpen && (
        <div className="mt-4 border-t border-slate-700 pt-4">
          <div className="space-y-3 mb-3 max-h-80 overflow-y-auto">
            {chatHistory.length === 0 && (
              <p className="text-slate-500 text-sm">
                Задайте уточняющий вопрос по этой карточке — например, «как это повлияет на наши
                закупки?».
              </p>
            )}
            {chatHistory.map((message, i) => (
              <div
                key={i}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    message.role === 'user'
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-700 text-slate-200'
                  }`}
                >
                  {message.text}
                  {message.role === 'ai' && message.demo && (
                    <div className="text-[10px] text-slate-400 mt-1">демо-ответ</div>
                  )}
                </div>
              </div>
            ))}
            {asking && <div className="text-slate-500 text-sm">Готовим ответ…</div>}
          </div>
          <form onSubmit={handleAsk} className="flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-purple-500"
              placeholder="Ваш вопрос по новости…"
            />
            <button
              type="submit"
              disabled={asking || !question.trim()}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer"
            >
              Отправить
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

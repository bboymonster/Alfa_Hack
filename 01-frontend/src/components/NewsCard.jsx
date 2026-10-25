import { useState } from 'react'

function formatDate(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
  } catch {
    return value
  }
}

function Tag({ children, tone = 'default' }) {
  const tones = {
    fact: 'border-sky-500/40 text-sky-300 bg-sky-500/10',
    risk: 'border-red-500/40 text-red-300 bg-red-500/10',
    opportunity: 'border-green-500/40 text-green-300 bg-green-500/10',
    action: 'border-purple-500/40 text-purple-300 bg-purple-500/10',
    bank: 'border-almond-500/40 text-amber-300 bg-amber-500/10',
    ai: 'border-fuchsia-500/40 text-fuchsia-300 bg-fuchsia-500/10',
    demo: 'border-amber-500/40 text-amber-300 bg-amber-500/10',
    trace: 'border-slate-500/40 text-slate-400 bg-slate-500/10',
    default: 'border-slate-500/40 text-slate-300 bg-slate-700/50',
  }
  return (
    <span className={`inline-flex items-center text-xs border px-2.5 py-1 rounded-md ${tones[tone] || tones.default}`}>
      {children}
    </span>
  )
}

const QUESTION_ICONS = {
  fact: '🗞️',
  why: '💡',
  risk: '⚠️',
  action: '📋',
  bank: '🏛️',
  trace: '🧭',
}

export default function NewsCard({ item, onAsk, onToggleFavorite }) {
  const { news, insight } = item
  const [question, setQuestion] = useState('')
  const [chatOpen, setChatOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [asking, setAsking] = useState(false)
  const [traceOpen, setTraceOpen] = useState(insight.agent_steps?.length > 0)

  async function handleAsk(e) {
    e.preventDefault()
    if (!question.trim() || asking) return
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

  const score = item.importance_score
  const scoreColor = score >= 8 ? 'text-red-400' : score >= 6 ? 'text-amber-400' : 'text-sky-400'

  return (
    <div
      className="relative bg-[--color-surface-card] border border-[--color-border] rounded-2xl shadow-xl hover:shadow-[--color-alfa-red]/5 transition-all duration-300 overflow-hidden group animate-fadeIn"
      data-rich="true"
    >
      {/* Верхняя акцентная полоска: уровень важности + избранное */}
      <div
        className="h-1.5"
        style={{ backgroundColor: `hsl(${(score / 10) * 120 + 0}, 90%, 40%)` }}
      />

      <div className="p-6 sm:p-8">
        {/* Шапка карточки: метаданные + кнопка избранного */}
        <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
          <div className="flex flex-wrap items-center gap-2.5 text-xs text-[--color-text-dim]">
            <Tag tone="fact">{QUESTION_ICONS.fact} Факт</Tag>
            <span className="hidden xs:inline">{news.source}</span>
            <span>•</span>
            <span>{formatDate(news.published_at)}</span>
            <Tag tone="default">{news.category}</Tag>
            <span className={`ml-auto font-semibold ${scoreColor}`}>Важность ${score}/10</span>
          </div>

          <button
            onClick={() => onToggleFavorite(item.id, !item.is_favorite)}
            className={`relative p-2 rounded-lg transition-all duration-200 ${
              item.is_favorite
                ? 'text-amber-400 scale-110'
                : 'text-[--color-text-dim] hover:text-amber-400 hover:scale-110'
            }`}
            aria-label={item.is_favorite ? 'Убрать из избранного' : 'В избранное'}
          >
            <svg
              className="w-5 h-5"
              viewBox="0 2 24 24"
              fill={item.is_favorite ? 'currentColor' : 'none'}
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 17.27L18.88 21 17 16.51 15.11 14.5 12 15.77 8.89 14.5 7 16.51 5.12 21z" />
            </svg>
            <span className="sr-only">избранное</span>
          </button>
        </div>

        {/* Q1 — Заголовок + факты */}
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-3 leading-tight">
          {news.title}
        </h2>
        <p className="text-[--color-text-dim] text-sm leading-relaxed mb-7">{news.summary_facts}</p>

        {/* Q2 — Почему важно */}
        <CardSection title="Почему это важно для вашей компании" icon={QUESTION_ICONS.why} tone="ai">
          <p className="text-[--color-text] text-sm leading-relaxed">{insight.why_it_matters}</p>
        </CardSection>

        {/* Q3 — Риски и возможности */}
        <CardSection title="Риски и возможности" icon={QUESTION_ICONS.risk} tone="risk">
          <div className="grid sm:grid-cols-2 gap-5">
            <ul className="space-y-1.5">
              <li className="text-xs font-semibold text-red-300 uppercase tracking-wide">Риски</li>
              {insight.risks?.length > 0 ? (
                insight.risks.map((risk, i) => (
                  <li key={i} className="text-[--color-text-dim] text-sm flex gap-2">
                    <span className="text-red-400">▲</span>
                    {risk}
                  </li>
                ))
              ) : (
                <li className="text-[--color-text-dim] text-sm">Риски не выявлены.</li>
              )}
            </ul>
            <ul className="space-y-1.5">
              <li className="text-xs font-semibold text-green-300 uppercase tracking-wide">Возможности</li>
              {insight.opportunities?.length > 0 ? (
                insight.opportunities.map((opp, i) => (
                  <li key={i} className="text-[--color-text-dim] text-sm flex gap-2">
                    <span className="text-green-400">✓</span>
                    {opp}
                  </li>
                ))
              ) : (
                <li className="text-[--color-text-dim] text-sm">Возможности не выявлены.</li>
              )}
            </ul>
          </div>
        </CardSection>

        {/* Q4 — Действия */}
        <CardSection title="Рекомендуемые действия" icon={QUESTION_ICONS.action} tone="action">
          <p className="text-[--color-text] text-sm leading-relaxed">{insight.action_item}</p>
        </CardSection>

        {/* Q5 — Позиция банка */}
        <CardSection title="Как это оценивает Альфа‑Банк" icon={QUESTION_ICONS.bank} tone="bank">
          {insight.alfa_bank_position ? (
            <>
              <p className="text-[--color-text] text-sm leading-relaxed">{insight.alfa_bank_position}</p>
              {(insight.alfa_report_name || insight.alfa_report_page) && (
                <p className="text-[--color-text-dim] text-xs mt-2">
                  Источник:{' '}
                  <span className="text-[--color-text]">
                    {insight.alfa_report_name}
                    {insight.alfa_report_page ? `, стр. ${insight.alfa_report_page}` : ''}
                  </span>
                </p>
              )}
            </>
          ) : (
            <p className="text-[--color-text-dim] text-sm">
              Релевантная позиция банка в корпусе отчётов не найдена (корпус не проиндексирован).
            </p>
          )}
        </CardSection>

        {/* Q6 — Основание вывода + трассировка */}
        <CardSection
          title="На чём основан вывод"
          icon={QUESTION_ICONS.trace}
          tone="trace"
          action={
            insight.agent_steps?.length > 0 ? (
              <button
                onClick={() => setTraceOpen((v) => !v)}
                className="text-[--color-text-dim] hover:text-[--color-text] transition-colors"
                aria-label={traceOpen ? 'Скрыть шаги агента' : 'Показать шаги агента'}
              >
                <svg
                  className={`w-4 h-4 transition-transform ${traceOpen ? 'rotate-180' : ''}`}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>
            ) : null
          }
        >
          {(insight.traceability?.matched_company_features?.length > 0) && (
            <div className="flex flex-wrap gap-2 mb-3">
              {insight.traceability.matched_company_features.map((feature) => (
                <Tag key={feature} tone="trace">
                  {feature}
                </Tag>
              ))}
            </div>
          )}
          {(insight.traceability?.verified_sources?.length > 0) && (
            <p className="text-[--color-text-dim] text-xs mb-2">
              Источники: {insight.traceability.verified_sources.join('; ')}
            </p>
          )}

          {traceOpen && insight.agent_steps?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-[--color-border]">
              <ol className="space-y-1.5 list-decimal list-inside">
                {insight.agent_steps.map((step, i) => (
                  <li key={i} className="text-[--color-text-dim] text-xs">
                    {step}
                  </li>
                ))}
              </ol>
              {insight.self_check && (
                <p className="text-xs mt-2 flex items-center gap-1.5">
                  {insight.self_check.passed ? (
                    <>
                      <span className="text-green-400">✓ Самопроверка пройдена</span>
                    </>
                  ) : (
                    <span className="text-red-400">✗ Самопроверка: есть нарушения</span>
                  )}
                  {insight.confidence != null && (
                    <span className="text-[--color-text-dim]">· уверенность {Math.round(insight.confidence * 100)}%</span>
                  )}
                </p>
              )}
            </div>
          )}
        </CardSection>

        {/* Метки происхождения */}
        <div className="flex flex-wrap gap-2 mt-6 pt-5 border-t border-[--color-border]">
          <Tag tone="fact">[Факт]</Tag>
          <Tag tone="bank">[Позиция банка]</Tag>
          <Tag tone="ai">[Вывод AI]</Tag>
          {item.is_demo && <Tag tone="demo">демо / без LLM</Tag>}
        </div>

        {/* Действия: спросить */}
        <div className="mt-6">
          <button
            onClick={() => setChatOpen((v) => !v)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-[--color-alfa-red] to-[--color-alfa-red-hover] hover:brightness-110 text-white text-sm font-medium shadow-lg shadow-[--color-alfa-red]/25 transition-all duration-200"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L15 11H22L13 17L16 22L12 18L8 22L11 17L2 11L9 11z" />
            </svg>
            Спросить нейросеть
          </button>
        </div>

        {/* Чат */}
        {chatOpen && (
          <div className="mt-5 pt-5 border-t border-[--color-border]">
            <div className="space-y-3 mb-3 max-h-80 overflow-y-auto">
              {chatHistory.length === 0 && (
                <p className="text-[--color-text-dim] text-sm">
                  Задайте уточняющий вопрос, например: «как это повлияет на наши закупки?».
                </p>
              )}
              {chatHistory.map((message, i) => (
                <div key={i} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[85%] rounded-xl px-4 py-3 text-sm ${
                      message.role === 'user'
                        ? 'bg-[--color-alfa-red] text-white'
                        : 'bg-[--color-surface-elev] text-[--color-text]'
                    }`}
                  >
                    {message.text}
                    {message.role === 'ai' && message.demo && (
                      <div className="text-[10px] text-[--color-text-dim] mt-1">демо‑ответ</div>
                    )}
                  </div>
                </div>
              ))}
              {asking && <div className="text-[--color-text-dim] text-sm">Готовим ответ…</div>}
            </div>
            <form onSubmit={handleAsk} className="flex gap-2">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="flex-1 px-4 py-2.5 bg-[--color-surface-elev] border border-[--color-border] rounded-lg text-white text-sm focus:border-[--color-alfa-red]"
                placeholder="Ваш вопрос по новости…"
                disabled={asking}
              />
<button
                type="submit"
                disabled={asking || !question.trim()}
                className="px-4 py-2 rounded-lg bg-[--color-alfa-gold] hover:brightness-110 disabled:opacity-50 text-[--color-surface] font-medium shadow-lg shadow-black/30 transition-all"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M2 21l21-9-21-9v7l15 2-15 2z" />
                </svg>
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}

function CardSection({ title, icon, tone, action, children }) {
  return (
    <div className="mb-5 last:mb-0">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <span>{icon}</span>
          <span className="text-white">{title}</span>
        </h3>
        {action}
      </div>
      {children}
    </div>
  )
}

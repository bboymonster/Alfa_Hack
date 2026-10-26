import { useEffect, useId, useRef, useState } from "react";
import Icon from "./Icon";

const SUMMARY_LIMIT = 210;
const FACTS_LIMIT = 175;
const NEXT_STEP_LIMIT = 140;
const HIGH_PRIORITY_SCORE = 8;

function compactText(value, limit = SUMMARY_LIMIT) {
  const text = (value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  const sentenceEnd = text.slice(0, limit).match(/^.*[.!?](?=\s|$)/u)?.[0];
  if (sentenceEnd && sentenceEnd.length >= 60) return sentenceEnd;
  const cut = text.lastIndexOf(" ", limit - 1);
  return `${text.slice(0, cut > 0 ? cut : limit - 1).trimEnd()}…`;
}

/** AI-сервис склеивает несколько действий через «; » — показываем их списком. */
function splitActions(value) {
  return (value || "")
    .split(/;\s+(?=[А-ЯA-Z])/u)
    .map((part) => part.trim().replace(/^[;.\s]+|[;\s]+$/g, ""))
    .filter(Boolean);
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function resolveHref(url) {
  if (!url) return undefined;
  try {
    const parsed = new URL(url, window.location.origin);
    if (!["http:", "https:"].includes(parsed.protocol)) return undefined;
    // Относительные ссылки (например, /articles/report.pdf#page=3) ведут на тот же origin.
    return url.startsWith("/") ? parsed.pathname + parsed.search + parsed.hash : parsed.href;
  } catch {
    return undefined;
  }
}

function SourceLink({ url, children }) {
  const href = resolveHref(url);
  return href ? (
    <a className="source-link" href={href} target="_blank" rel="noreferrer noopener">
      {children}
      <Icon name="link" size={14} />
    </a>
  ) : (
    <span className="source-text">{children}</span>
  );
}

function AnalysisSection({ number, title, children }) {
  return (
    <section className="analysis-section">
      <div className="section-number" aria-hidden="true">
        {number}
      </div>
      <div className="section-content">
        <h3>{title}</h3>
        {children}
      </div>
    </section>
  );
}

function BulletList({ items, fallback, tone }) {
  if (!items?.length) return <p className="muted">{fallback}</p>;
  return (
    <ul className={`bullet-list ${tone ? `bullet-${tone}` : ""}`}>
      {items.map((text, index) => (
        <li key={index}>{text}</li>
      ))}
    </ul>
  );
}

export default function NewsCard({ item, onAsk, onToggleFavorite }) {
  const news = item.news ?? {};
  const insight = item.insight ?? {};
  const chatId = useId();
  const inputRef = useRef(null);
  const messagesRef = useRef(null);
  const [question, setQuestion] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [asking, setAsking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const score = Number(item.importance_score) || 0;
  const isHigh = score >= HIGH_PRIORITY_SCORE;
  const dateLabel = formatDate(news.published_at);
  const actions = splitActions(insight.action_item);
  const selfCheck = insight.self_check;
  const confidence =
    typeof insight.confidence === "number"
      ? Math.round(insight.confidence * 100)
      : null;

  useEffect(() => {
    if (chatOpen) inputRef.current?.focus();
  }, [chatOpen]);

  useEffect(() => {
    const node = messagesRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [chatHistory, asking]);

  async function handleFavorite() {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      await onToggleFavorite(item.id, !item.is_favorite);
    } catch (err) {
      setError(err?.message || "Не удалось сохранить карточку. Попробуйте ещё раз.");
    } finally {
      setSaving(false);
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    const q = question.trim();
    if (!q || asking) return;
    setQuestion("");
    setChatHistory((history) => [...history, { role: "user", text: q }]);
    setAsking(true);
    try {
      const result = await onAsk(item.id, q);
      setChatHistory((history) => [
        ...history,
        {
          role: "ai",
          text: result?.answer || "Ответ пустой. Попробуйте переформулировать вопрос.",
          demo: result?.is_demo,
          mode: result?.mode,
          offTopic: result?.on_topic === false,
          sources: Array.isArray(result?.sources) ? result.sources : [],
        },
      ]);
    } catch (err) {
      setChatHistory((history) => [
        ...history,
        {
          role: "error",
          text: err?.message || "Не удалось получить ответ. Повторите вопрос.",
          retry: q,
        },
      ]);
    } finally {
      setAsking(false);
      inputRef.current?.focus();
    }
  }

  function handleChatKeyDown(event) {
    if (event.key === "Escape") {
      event.stopPropagation();
      setChatOpen(false);
    }
  }

  const modeLabel =
    insight.mode === "llm"
      ? item.is_demo
        ? "Вывод AI · демо-новость"
        : "Вывод AI"
      : "Демо · без LLM";

  return (
    <article className={`news-card ${isHigh ? "is-high" : ""}`}>
      <div className="card-meta">
        <span className="category-badge" title={news.category}>
          {news.category || "Без темы"}
        </span>
        {dateLabel && <time dateTime={news.published_at}>{dateLabel}</time>}
        <span
          className={`score-badge ${isHigh ? "score-high" : ""}`}
          title="Оценка важности новости для вашей компании и роли"
        >
          {isHigh && <span className="status-dot" />}
          Важность {score}/10
        </span>
        <button
          type="button"
          className={`icon-button favorite-button ${item.is_favorite ? "is-saved" : ""}`}
          onClick={handleFavorite}
          disabled={saving}
          aria-busy={saving}
          aria-label={item.is_favorite ? "Убрать из избранного" : "В избранное"}
          aria-pressed={item.is_favorite}
          title={item.is_favorite ? "Убрать из избранного" : "В избранное"}
        >
          <Icon name="bookmark" fill={item.is_favorite ? "currentColor" : "none"} />
        </button>
      </div>
      <div className="card-pair">
        <div className="news-preview">
          <span className="eyebrow">НОВОСТЬ · ФАКТ</span>
          <h2 title={news.title}>{news.title}</h2>
          <p>{compactText(news.summary_facts, FACTS_LIMIT)}</p>
          <div className="news-source">
            <SourceLink url={news.source_url}>{news.source || "Источник не указан"}</SourceLink>
          </div>
        </div>
        <div className="insight-preview">
          <span className="eyebrow insight-label">
            <Icon name="spark" size={15} /> ЧТО ЭТО ЗНАЧИТ ДЛЯ ВАС
          </span>
          <p className="insight-summary">{compactText(insight.why_it_matters)}</p>
          {actions.length > 0 && (
            <div className="next-step">
              <span>Следующий шаг</span>
              <p>{compactText(actions[0], NEXT_STEP_LIMIT)}</p>
              {actions.length > 1 && (
                <small>Ещё {actions.length - 1} в подробном анализе</small>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="card-bottom">
        <span
          className={`badge ${item.is_demo ? "badge-demo" : "badge-live"}`}
          title={
            insight.mode === "llm"
              ? "Анализ сгенерирован языковой моделью"
              : "Детерминированный анализ без вызова модели"
          }
        >
          {modeLabel}
        </span>
        <button
          type="button"
          className={`button button-subtle ${chatOpen ? "is-active" : ""}`}
          onClick={() => setChatOpen((value) => !value)}
          aria-expanded={chatOpen}
          aria-controls={chatId}
        >
          <Icon name="spark" size={16} />
          {chatOpen ? "Скрыть диалог" : "Спросить по новости"}
        </button>
      </div>
      <details className="analysis-details">
        <summary>
          <span>Подробный анализ</span>
          <span className="detail-hint">Риски, действия и источники</span>
          <Icon name="chevron" size={18} />
        </summary>
        <div className="analysis-body">
          <AnalysisSection number="01" title="Что произошло">
            <p>{news.summary_facts}</p>
            <SourceLink url={news.source_url}>{news.source || "Источник не указан"}</SourceLink>
          </AnalysisSection>
          <AnalysisSection number="02" title="Почему это важно для компании">
            <p>{insight.why_it_matters}</p>
          </AnalysisSection>
          <AnalysisSection number="03" title="Риски и возможности">
            <div className="risk-grid">
              <div>
                <h4 className="risk-label">Риски</h4>
                <BulletList
                  items={insight.risks}
                  tone="risk"
                  fallback="Риски не выявлены в доступных данных."
                />
              </div>
              <div>
                <h4 className="opportunity-label">Возможности</h4>
                <BulletList
                  items={insight.opportunities}
                  tone="opportunity"
                  fallback="Возможности не выявлены в доступных данных."
                />
              </div>
            </div>
          </AnalysisSection>
          <AnalysisSection number="04" title="Рекомендуемые действия">
            {actions.length > 1 ? (
              <ol className="action-list">
                {actions.map((text, index) => (
                  <li key={index}>{text}</li>
                ))}
              </ol>
            ) : (
              <p>{actions[0] || "Конкретные действия не сформированы."}</p>
            )}
          </AnalysisSection>
          <AnalysisSection number="05" title="Позиция Альфа-Банка">
            {insight.alfa_bank_position ? (
              <>
                <blockquote>{insight.alfa_bank_position}</blockquote>
                {insight.alfa_report_name && (
                  <SourceLink url={insight.alfa_report_url}>
                    {insight.alfa_report_name}
                    {insight.alfa_report_page ? `, стр. ${insight.alfa_report_page}` : ""}
                  </SourceLink>
                )}
              </>
            ) : (
              <p className="muted">
                Подтверждённая позиция банка по этой новости в доступных отчётах не
                найдена.
              </p>
            )}
          </AnalysisSection>
          <AnalysisSection number="06" title="На чём основан вывод">
            {insight.traceability?.matched_company_features?.length > 0 && (
              <div className="feature-tags">
                {insight.traceability.matched_company_features.map((feature) => (
                  <span className="badge" key={feature}>
                    {feature}
                  </span>
                ))}
              </div>
            )}
            <BulletList
              items={insight.traceability?.verified_sources}
              fallback="Источники вывода: сама новость и профиль компании."
            />
            {!!insight.agent_steps?.length && (
              <details className="processing-details">
                <summary>
                  Как подготовлен анализ
                  <Icon name="chevron" size={16} />
                </summary>
                <ol>
                  {insight.agent_steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ol>
                {selfCheck && (
                  <div className={`self-check ${selfCheck.passed ? "is-passed" : "is-flagged"}`}>
                    <Icon name={selfCheck.passed ? "check" : "alert"} size={14} />
                    <span>
                      {selfCheck.passed
                        ? "Проверка согласованности пройдена"
                        : "Проверка обнаружила замечания"}
                      {selfCheck.attempts > 1 ? ` · попыток: ${selfCheck.attempts}` : ""}
                      {confidence !== null ? ` · уверенность ${confidence}%` : ""}
                    </span>
                    {!selfCheck.passed && !!selfCheck.violations?.length && (
                      <ul>
                        {selfCheck.violations.map((text, index) => (
                          <li key={index}>{text}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </details>
            )}
          </AnalysisSection>
        </div>
      </details>
      {error && (
        <p className="error-message card-error" role="alert">
          {error}
        </p>
      )}
      {chatOpen && (
        <section
          className="card-chat"
          id={chatId}
          aria-label="Диалог по новости"
          onKeyDown={handleChatKeyDown}
        >
          <div className="chat-head">
            <div>
              <h3>Разберём вашу ситуацию</h3>
              <p className="muted">Например: «Как это повлияет на наши закупки?»</p>
            </div>
            <button
              type="button"
              className="icon-button"
              onClick={() => setChatOpen(false)}
              aria-label="Закрыть диалог"
              title="Закрыть (Esc)"
            >
              <Icon name="close" size={18} />
            </button>
          </div>
          <div className="chat-messages" role="log" aria-live="polite" ref={messagesRef}>
            {chatHistory.length === 0 && !asking && (
              <p className="chat-empty muted">
                Задайте вопрос — ответ учтёт новость, профиль компании и отчёты банка.
              </p>
            )}
            {chatHistory.map((message, index) => (
              <div key={index} className={`chat-message message-${message.role}`}>
                <p>{message.text}</p>
                {message.offTopic && (
                  <span className="muted">Вопрос вне темы карточки — ответ ограничен.</span>
                )}
                {message.demo && (
                  <span className="muted">
                    {message.mode === "llm" ? "Ответ AI · демо-данные" : "Демо-ответ · без LLM"}
                  </span>
                )}
                {!!message.sources?.length && (
                  <div className="chat-sources">
                    {message.sources.map((source, i) => (
                      <SourceLink key={i} url={source.url}>
                        {source.title}
                        {source.page ? `, стр. ${source.page}` : ""}
                      </SourceLink>
                    ))}
                  </div>
                )}
                {message.role === "error" && !asking && (
                  <button
                    type="button"
                    className="chat-retry"
                    onClick={() => setQuestion(message.retry)}
                  >
                    Вернуть вопрос в поле
                  </button>
                )}
              </div>
            ))}
            {asking && (
              <div className="chat-message message-ai chat-typing" role="status">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="sr-only">Готовим ответ…</span>
              </div>
            )}
          </div>
          <form className="chat-form" onSubmit={handleAsk}>
            <input
              ref={inputRef}
              aria-label="Вопрос по новости"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ваш вопрос по новости"
              maxLength={2000}
              autoComplete="off"
              disabled={asking}
            />
            <button
              type="submit"
              className="button button-primary"
              disabled={asking || !question.trim()}
              aria-label={asking ? "Отправляем вопрос" : "Отправить вопрос"}
              aria-busy={asking}
            >
              {asking ? <span className="spinner" aria-hidden="true" /> : <Icon name="send" size={18} />}
            </button>
          </form>
        </section>
      )}
    </article>
  );
}

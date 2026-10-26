import { useId, useState } from "react";
import Icon from "./Icon";

function compactText(value, limit = 210) {
  const text = (value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  const sentenceEnd = text.slice(0, limit).match(/^.*[.!?](?=\s|$)/u)?.[0];
  if (sentenceEnd && sentenceEnd.length >= 60) return sentenceEnd;
  const cut = text.lastIndexOf(" ", limit - 1);
  return `${text.slice(0, cut > 0 ? cut : limit - 1).trimEnd()}…`;
}

function SourceLink({ url, children }) {
  let href;
  try {
    const parsed = new URL(url);
    if (["http:", "https:"].includes(parsed.protocol)) href = parsed.href;
  } catch {
    /* Источники без ссылки остаются текстом. */
  }
  return href ? (
    <a className="source-link" href={href} target="_blank" rel="noreferrer">
      {children}
      <Icon name="link" size={14} />
    </a>
  ) : (
    <span>{children}</span>
  );
}

function AnalysisSection({ number, title, children }) {
  return (
    <section className="analysis-section">
      <div className="section-number">{number}</div>
      <div>
        <h3>{title}</h3>
        {children}
      </div>
    </section>
  );
}

export default function NewsCard({ item, onAsk, onToggleFavorite }) {
  const { news, insight } = item;
  const chatId = useId();
  const [question, setQuestion] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [asking, setAsking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const score = item.importance_score;
  const date = new Date(news.published_at);
  const dateLabel = Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });

  async function handleFavorite() {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      await onToggleFavorite(item.id, !item.is_favorite);
    } catch (err) {
      setError(
        err?.message || "Не удалось сохранить карточку. Попробуйте ещё раз.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    if (!question.trim() || asking) return;
    const q = question.trim();
    setQuestion("");
    setChatHistory((history) => [...history, { role: "user", text: q }]);
    setAsking(true);
    try {
      const result = await onAsk(item.id, q);
      setChatHistory((history) => [
        ...history,
        {
          role: "ai",
          text: result.answer,
          demo: result.is_demo,
          mode: result.mode,
          sources: result.sources,
        },
      ]);
    } catch (err) {
      setChatHistory((history) => [
        ...history,
        {
          role: "error",
          text: err?.message || "Не удалось получить ответ. Повторите вопрос.",
        },
      ]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <article className="news-card">
      <div className="card-meta">
        <span className="category-badge">{news.category}</span>
        <time dateTime={news.published_at}>{dateLabel}</time>
        <span className={`score-badge ${score >= 8 ? "score-high" : ""}`}>
          {score >= 8 && <span className="status-dot" />}Важность {score}/10
        </span>
        <button
          className={`icon-button favorite-button ${item.is_favorite ? "is-saved" : ""}`}
          onClick={handleFavorite}
          disabled={saving}
          aria-label={item.is_favorite ? "Убрать из избранного" : "В избранное"}
          aria-pressed={item.is_favorite}
        >
          <Icon
            name="bookmark"
            fill={item.is_favorite ? "currentColor" : "none"}
          />
        </button>
      </div>
      <div className="card-pair">
        <div className="news-preview">
          <span className="eyebrow">НОВОСТЬ · ФАКТ</span>
          <h2>{news.title}</h2>
          <p>{compactText(news.summary_facts, 175)}</p>
          <div className="news-source">
            <SourceLink url={news.source_url}>{news.source}</SourceLink>
          </div>
        </div>
        <div className="insight-preview">
          <span className="eyebrow insight-label">
            <Icon name="spark" size={15} /> ЧТО ЭТО ЗНАЧИТ ДЛЯ ВАС
          </span>
          <p className="insight-summary">
            {compactText(insight.why_it_matters)}
          </p>
          <div className="next-step">
            <span>Следующий шаг</span>
            <p>{compactText(insight.action_item, 140)}</p>
          </div>
        </div>
      </div>
      <div className="card-bottom">
        <span className={`badge ${item.is_demo ? "badge-demo" : "badge-live"}`}>
          {insight.mode === "llm"
            ? item.is_demo
              ? "Вывод AI · демо-новость"
              : "Вывод AI"
            : "Демо · без LLM"}
        </span>
        <button
          className="button button-subtle"
          onClick={() => setChatOpen((value) => !value)}
          aria-expanded={chatOpen}
          aria-controls={chatId}
        >
          <Icon name="spark" size={16} />
          Спросить по новости
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
            <SourceLink url={news.source_url}>{news.source}</SourceLink>
          </AnalysisSection>
          <AnalysisSection number="02" title="Почему это важно для компании">
            <p>{insight.why_it_matters}</p>
          </AnalysisSection>
          <AnalysisSection number="03" title="Риски и возможности">
            <div className="risk-grid">
              <div>
                <h4 className="risk-label">Риски</h4>
                <ul>
                  {insight.risks?.length ? (
                    insight.risks.map((text, index) => (
                      <li key={index}>{text}</li>
                    ))
                  ) : (
                    <li>Риски не выявлены в доступных данных.</li>
                  )}
                </ul>
              </div>
              <div>
                <h4 className="opportunity-label">Возможности</h4>
                <ul>
                  {insight.opportunities?.length ? (
                    insight.opportunities.map((text, index) => (
                      <li key={index}>{text}</li>
                    ))
                  ) : (
                    <li>Возможности не выявлены в доступных данных.</li>
                  )}
                </ul>
              </div>
            </div>
          </AnalysisSection>
          <AnalysisSection number="04" title="Рекомендуемые действия">
            <p>{insight.action_item}</p>
          </AnalysisSection>
          <AnalysisSection number="05" title="Позиция Альфа-Банка">
            {insight.alfa_bank_position ? (
              <>
                <blockquote>{insight.alfa_bank_position}</blockquote>
                {insight.alfa_report_name && (
                  <SourceLink url={insight.alfa_report_url}>
                    {insight.alfa_report_name}
                    {insight.alfa_report_page
                      ? `, стр. ${insight.alfa_report_page}`
                      : ""}
                  </SourceLink>
                )}
              </>
            ) : (
              <p className="muted">
                Подтверждённая позиция банка по этой новости в доступных отчётах
                не найдена.
              </p>
            )}
          </AnalysisSection>
          <AnalysisSection number="06" title="На чём основан вывод">
            <div className="feature-tags">
              {insight.traceability?.matched_company_features?.map(
                (feature) => (
                  <span className="badge" key={feature}>
                    {feature}
                  </span>
                ),
              )}
            </div>
            <ul>
              {insight.traceability?.verified_sources?.map((source, index) => (
                <li key={index}>{source}</li>
              ))}
            </ul>
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
                {insight.self_check && (
                  <p
                    className={
                      insight.self_check.passed
                        ? "opportunity-label"
                        : "risk-label"
                    }
                  >
                    {insight.self_check.passed
                      ? "Проверка согласованности пройдена."
                      : "Проверка обнаружила замечания."}
                  </p>
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
        >
          <h3>Разберём вашу ситуацию</h3>
          <p className="muted">Например: «Как это повлияет на наши закупки?»</p>
          <div className="chat-messages" role="log" aria-live="polite">
            {chatHistory.map((message, index) => (
              <div
                key={index}
                className={`chat-message message-${message.role}`}
              >
                <p>{message.text}</p>
                {message.demo && (
                  <span className="muted">
                    {message.mode === "llm"
                      ? "Ответ AI · демо-данные"
                      : "Демо-ответ · без LLM"}
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
              </div>
            ))}
            {asking && (
              <p className="muted" role="status">
                Готовим ответ…
              </p>
            )}
          </div>
          <form className="chat-form" onSubmit={handleAsk}>
            <input
              aria-label="Вопрос по новости"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ваш вопрос по новости"
              maxLength={2000}
              disabled={asking}
            />
            <button
              className="button button-primary"
              disabled={asking || !question.trim()}
              aria-label="Отправить вопрос"
            >
              <Icon name="send" size={18} />
            </button>
          </form>
        </section>
      )}
    </article>
  );
}

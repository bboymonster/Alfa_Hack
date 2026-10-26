/** Скелетон карточки «Новость-Инсайт»: повторяет геометрию NewsCard, чтобы макет не прыгал. */
export function CardSkeleton() {
  return (
    <div className="news-card skeleton-card" aria-hidden="true">
      <div className="card-meta">
        <span className="skeleton skeleton-pill" style={{ width: 120 }} />
        <span className="skeleton skeleton-line" style={{ width: 90 }} />
        <span
          className="skeleton skeleton-line"
          style={{ width: 80, marginLeft: "auto" }}
        />
      </div>
      <div className="card-pair">
        <div className="news-preview">
          <span className="skeleton skeleton-line" style={{ width: 90 }} />
          <span className="skeleton skeleton-title" style={{ width: "85%" }} />
          <span className="skeleton skeleton-line" style={{ width: "95%" }} />
          <span className="skeleton skeleton-line" style={{ width: "70%" }} />
        </div>
        <div className="insight-preview">
          <span className="skeleton skeleton-line" style={{ width: 150 }} />
          <span className="skeleton skeleton-line" style={{ width: "100%" }} />
          <span className="skeleton skeleton-line" style={{ width: "92%" }} />
          <span className="skeleton skeleton-block" />
        </div>
      </div>
      <div className="card-bottom">
        <span className="skeleton skeleton-pill" style={{ width: 96 }} />
        <span className="skeleton skeleton-pill" style={{ width: 150, height: 32 }} />
      </div>
    </div>
  );
}

export function FeedSkeleton({ count = 3 }) {
  return (
    <div className="feed-list" role="status" aria-label="Загружаем ленту">
      {Array.from({ length: count }, (_, index) => (
        <CardSkeleton key={index} />
      ))}
    </div>
  );
}

export function TextSkeleton({ width = 48 }) {
  return (
    <span
      className="skeleton skeleton-title"
      style={{ width, display: "inline-block" }}
      aria-hidden="true"
    />
  );
}

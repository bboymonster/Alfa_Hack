import { useEffect } from "react";
import Icon from "./Icon";

const AUTO_HIDE_MS = 6000;

/** Ненавязчивое уведомление внизу экрана. Закрывается само, по кнопке и по Escape. */
export default function Toast({ notice, onClose }) {
  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(onClose, AUTO_HIDE_MS);
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", onKey);
    };
  }, [notice, onClose]);

  if (!notice) return null;
  const tone = notice.tone || "info";
  return (
    <div
      className={`toast toast-${tone}`}
      role={tone === "error" ? "alert" : "status"}
      aria-live="polite"
    >
      <span className="toast-text">{notice.text}</span>
      {notice.action && (
        <button type="button" className="toast-action" onClick={notice.action.onClick}>
          {notice.action.label}
        </button>
      )}
      <button
        type="button"
        className="icon-button toast-close"
        onClick={onClose}
        aria-label="Закрыть уведомление"
      >
        <Icon name="close" size={16} />
      </button>
    </div>
  );
}

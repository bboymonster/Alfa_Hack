"""Проверки границы backend ↔ AI: настоящий HTTP, без LLM и внешней сети."""

import json
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient

from app.ai_client import AiClient
from app.config import Settings
from app.main import create_app
from app.store import MemoryStore


def insight_reply(body, mode="offline"):
    return {
        "request_id": "upstream-insight-1",
        "mode": mode,
        "card": {
            "why_it_matters": "Тестовый персональный контекст компании.",
            "risks": ["Тестовый риск"],
            "opportunities": [],
            "action_item": "Проверить тестовый сценарий.",
            "traceability": {
                "matched_company_features": ["CL_PRODUCT_LOA_MARK=1"],
                "verified_sources": ["Тестовый источник"],
            },
        },
        "importance": {"news_id": body["news"]["id"], "score": 8},
        "traceability": {
            "agent_steps": ["plan", "gather", "self_check", "finalize"],
            "self_check": {"passed": True, "attempts": 1, "violations": [], "fixed": []},
            "confidence": 0.75,
        },
        "latency_ms": 12,
    }


def chat_reply(body, mode="offline"):
    return {
        "request_id": "upstream-chat-1",
        "mode": mode,
        "answer": "Тестовый ответ по контексту новости.",
        "on_topic": False,
        "sources": [{"kind": "news", "title": "Источник теста", "url": "https://example.com"}],
    }


@pytest.fixture
def upstream():
    class Stub:
        status = 200
        raw = None
        transform = None
        mode = "offline"
        calls = []

    stub = Stub()
    stub.calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            stub.calls.append((self.path, body))
            data = (insight_reply if self.path == "/v1/insight" else chat_reply)(body, stub.mode)
            if stub.transform:
                data = stub.transform(deepcopy(data))
            if stub.status != 200:
                data = {"error": {"code": "TEST_ERROR", "request_id": "remote-error-id"}}
            encoded = stub.raw if stub.raw is not None else json.dumps(data).encode()
            self.send_response(stub.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    worker.start()
    stub.url = f"http://127.0.0.1:{server.server_port}"
    yield stub
    server.shutdown()
    server.server_close()
    worker.join(timeout=2)


@pytest.fixture
def ai_context(upstream):
    settings = Settings(
        _env_file=None,
        ai_service_enabled=True,
        ai_service_url=upstream.url,
        ai_service_timeout_s=1,
        ai_service_retry_interval_s=0.05,
    )
    store = MemoryStore()
    item = next(iter(store.feed.values()))
    return AiClient(settings), item, store.companies[item.company_id], settings


def ask(ai, item, company):
    return ai.answer_question(
        item.news, item.insight, company, item.role, "Что проверить?", item_id=item.id
    )


def wait_for(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    pytest.fail("Фоновое обогащение не завершилось в отведённое время")


@pytest.mark.parametrize("mode", ["offline", "llm"])
def test_real_http_maps_insight_trace_and_mode(upstream, ai_context, mode):
    ai, item, company, _ = ai_context
    upstream.mode = mode
    insight, score, is_demo = ai.generate_insight(item.news, company, item.role)
    assert score == 8
    assert insight.agent_steps == ["plan", "gather", "self_check", "finalize"]
    assert insight.self_check.passed is True
    assert insight.confidence == 0.75
    assert insight.mode == mode
    assert is_demo is (mode == "offline")
    path, sent = upstream.calls[0]
    assert path == "/v1/insight"
    assert sent["company"]["synthetic_u"] == company.synthetic_u
    assert sent["news"]["id"] == item.news.id
    assert sent["role"] == item.role.value
    assert ai.runtime_status() == ("available", mode)


@pytest.mark.parametrize("mode", ["offline", "llm"])
def test_chat_keeps_sources_on_topic_and_request_id(upstream, ai_context, mode):
    ai, item, company, _ = ai_context
    upstream.mode = mode
    response = ask(ai, item, company)
    assert response.mode == mode
    assert response.is_demo is (mode == "offline")
    assert response.on_topic is False
    assert response.request_id == "upstream-chat-1"
    assert response.sources[0].url == "https://example.com"
    path, body = upstream.calls[0]
    assert path == "/v1/ask"
    assert set(body["card"]) == {
        "why_it_matters",
        "risks",
        "opportunities",
        "action_item",
        "alfa_bank_position",
        "alfa_report_name",
        "alfa_report_page",
        "alfa_report_url",
        "traceability",
    }


@pytest.mark.parametrize("status", [422, 503])
def test_http_errors_return_fallback_and_log_remote_id(upstream, ai_context, caplog, status):
    ai, item, company, _ = ai_context
    upstream.status = status
    assert ai.generate_insight(item.news, company, item.role) is None
    response = ask(ai, item, company)
    assert response.mode == "mock" and response.is_demo
    assert response.sources == [] and response.on_topic is None
    assert "remote-error-id" in caplog.text
    assert f"http_{status}" in caplog.text
    assert ai.runtime_status() == ("unavailable", "mock")
    assert ai.retryable is (status >= 500)


@pytest.mark.parametrize("raw", [b"not json", b"[]", b"null", b"{}"])
def test_malformed_json_and_shapes_never_break_chat_or_worker(upstream, ai_context, raw):
    ai, item, company, _ = ai_context
    upstream.raw = raw
    assert ai.generate_insight(item.news, company, item.role) is None
    assert ask(ai, item, company).is_demo is True
    assert ai.retryable is False


@pytest.mark.parametrize("bad_field", ["card", "confidence", "score", "mode", "news_id"])
def test_invalid_insight_contract_is_rejected(upstream, ai_context, bad_field):
    ai, item, company, _ = ai_context

    def invalidate(data):
        if bad_field == "card":
            data["card"] = {}
        elif bad_field == "confidence":
            data["traceability"]["confidence"] = 1.5
        elif bad_field == "score":
            data["importance"]["score"] = 99
        elif bad_field == "news_id":
            data["importance"]["news_id"] = "different-news"
        else:
            data["mode"] = "unknown"
        return data

    upstream.transform = invalidate
    assert ai.generate_insight(item.news, company, item.role) is None
    assert ai.runtime_status() == ("unavailable", "mock")
    assert ai.retryable is False


def test_timeout_is_a_retryable_fallback(ai_context, monkeypatch):
    ai, item, company, _ = ai_context

    def timeout(*args, **kwargs):
        raise TimeoutError("upstream timeout")

    monkeypatch.setattr("urllib.request.urlopen", timeout)
    assert ai.generate_insight(item.news, company, item.role) is None
    assert ask(ai, item, company).is_demo is True
    assert ai.retryable is True


def test_disabled_ai_never_uses_network(upstream, ai_context):
    _, item, company, settings = ai_context
    ai = AiClient(settings.model_copy(update={"ai_service_enabled": False}))
    assert ai.generate_insight(item.news, company, item.role) is None
    assert ask(ai, item, company).mode == "mock"
    assert upstream.calls == []
    assert ai.runtime_status() == ("disabled", "mock")


def test_lifespan_enriches_and_keeps_synthetic_news_marked_demo(upstream, ai_context):
    _, _, _, settings = ai_context
    upstream.mode = "llm"
    app = create_app(settings)
    assert upstream.calls == []  # Создание приложения не запускает сетевые потоки.
    with TestClient(app) as client:
        wait_for(lambda: app.state.store.enrichment_status().status == "complete")
        health = client.get("/health").json()
        assert health["ai"] == "ai-service" and health["ai_mode"] == "llm"
        assert health["enrichment"]["completed"] == 27
        token = client.post(
            "/api/auth/login", json={"email": "alfa-hack-2026", "password": "password123"}
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        feed = client.get("/api/feed", headers=headers).json()
        assert feed["is_demo"] is True
        assert all(item["is_demo"] for item in feed["items"])
        assert feed["items"][0]["insight"]["mode"] == "llm"
        item = feed["items"][0]
        reply = client.post(
            f"/api/feed/{item['id']}/ask", json={"question": "Что проверить?"}, headers=headers
        ).json()
        assert reply["mode"] == "llm" and reply["is_demo"] is True
        assert reply["sources"][0]["kind"] == "news"


def test_background_recovers_after_ai_becomes_available(upstream, ai_context):
    _, _, _, settings = ai_context
    upstream.status = 503
    app = create_app(settings)
    with TestClient(app) as client:
        wait_for(lambda: app.state.store.enrichment_status().status == "retrying")
        assert client.get("/health").json()["ai_status"] == "unavailable"
        upstream.status = 200
        wait_for(lambda: app.state.store.enrichment_status().status == "complete")
        assert client.get("/health").json()["ai_mode"] == "offline"
        assert app.state.store.enrichment_status().completed == 27


def test_contract_error_stops_background_without_retries(upstream, ai_context):
    _, _, _, settings = ai_context
    upstream.status = 422
    app = create_app(settings)
    with TestClient(app):
        wait_for(lambda: app.state.store.enrichment_status().status == "failed")
        assert len(upstream.calls) == 1
        assert all(item.insight.mode == "mock" for item in app.state.store.feed.values())


def test_shutdown_interrupts_long_retry_wait(upstream, ai_context):
    _, _, _, settings = ai_context
    upstream.status = 503
    app = create_app(settings.model_copy(update={"ai_service_retry_interval_s": 300}))
    with TestClient(app):
        wait_for(lambda: app.state.store.enrichment_status().status == "retrying")
    assert app.state.store.enrichment_status().status == "stopped"
    assert len(upstream.calls) == 1


def test_feed_demo_flag_reflects_selected_cards(client, headers):
    store = client.app.state.store
    for item in store.feed.values():
        item.is_demo = False
    response = client.get("/api/feed", headers=headers).json()
    assert response["is_demo"] is False
    store.feed[response["items"][0]["id"]].is_demo = True
    assert client.get("/api/feed", headers=headers).json()["is_demo"] is True


def test_parallel_chat_error_does_not_cancel_retryable_enrichment(upstream, ai_context):
    ai, item, company, _ = ai_context
    upstream.status = 503
    failed = Event()
    resume = Event()
    result = {}

    def enrichment_request():
        ai.generate_insight(item.news, company, item.role)
        failed.set()
        if resume.wait(timeout=2):
            result["retryable"] = ai.retryable

    worker = Thread(target=enrichment_request)
    worker.start()
    try:
        assert failed.wait(timeout=2)
        upstream.status = 422
        assert ask(ai, item, company).mode == "mock"
        assert ai.retryable is False
    finally:
        resume.set()
        worker.join(timeout=2)
    assert result["retryable"] is True


@pytest.mark.parametrize(
    ("category", "topic"),
    [
        ("Финансы и макроэкономика", "monetary_policy"),
        ("Логистика", "logistics_trade"),
        ("Регулирование", "regulation_tax"),
        ("Логистика и внешняя торговля", "logistics_trade"),
        ("Новая неизвестная категория", None),
    ],
)
def test_known_categories_keep_their_topic_at_ai_boundary(upstream, ai_context, category, topic):
    ai, item, company, _ = ai_context
    news = item.news.model_copy(update={"category": category})
    assert ai.generate_insight(news, company, item.role) is not None
    sent = upstream.calls[0][1]["news"]
    assert sent["category"] == category
    assert sent.get("topic") == topic

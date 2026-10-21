from math import ceil
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.auth import CurrentUser
from app.mock_ai import answer_news_question
from app.schemas import (
    AskRequest,
    AskResponse,
    Company,
    FavoriteRequest,
    FavoriteResponse,
    FeedItem,
    FeedResponse,
    Role,
    User,
)
from app.store import MemoryStore

router = APIRouter(prefix="/api", tags=["Компании и лента"])


def check_company(store: MemoryStore, company_id: str, user: User) -> None:
    if company_id not in store.companies:
        raise HTTPException(status_code=404, detail="Компания не найдена.")
    if company_id not in user.allowed_company_ids:
        raise HTTPException(status_code=403, detail="Нет доступа к этой компании.")


def find_item(store: MemoryStore, item_id: str, user: User) -> FeedItem:
    item = store.feed.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Карточка не найдена.")
    check_company(store, item.company_id, user)
    return item


@router.get("/companies", response_model=list[Company], summary="Компании, доступные пользователю")
def companies(request: Request, user: CurrentUser) -> list[Company]:
    return [
        company
        for company in request.app.state.store.companies.values()
        if company.synthetic_u in user.allowed_company_ids
    ]


@router.get("/feed", response_model=FeedResponse, summary="Лента «Новость — Инсайт»")
def feed(
    request: Request,
    user: CurrentUser,
    company_id: str | None = None,
    role: Role | None = None,
    category: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    favorites_only: bool = False,
) -> FeedResponse:
    store = request.app.state.store
    selected_company = company_id or user.current_company_id
    selected_role = role or user.role
    check_company(store, selected_company, user)
    items = [
        store.with_favorite(item, user)
        for item in store.feed.values()
        if item.company_id == selected_company
        and item.role == selected_role
        and (category is None or item.news.category == category)
    ]
    if favorites_only:
        items = [item for item in items if item.is_favorite]
    items.sort(key=lambda item: (item.importance_score, item.news.published_at), reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    return FeedResponse(
        items=items[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size),
    )


@router.get("/feed/{item_id}", response_model=FeedItem, summary="Детальная карточка")
def detail(item_id: str, request: Request, user: CurrentUser) -> FeedItem:
    store = request.app.state.store
    return store.with_favorite(find_item(store, item_id, user), user)


@router.post(
    "/feed/{item_id}/favorite", response_model=FavoriteResponse, summary="Изменить закладку"
)
def favorite(
    item_id: str, body: FavoriteRequest, request: Request, user: CurrentUser
) -> FavoriteResponse:
    store = request.app.state.store
    item = find_item(store, item_id, user)
    key = (user.id, item.news.id)
    with store.lock:
        if body.is_favorite:
            store.favorites.add(key)
        else:
            store.favorites.discard(key)
    return FavoriteResponse(id=item_id, is_favorite=body.is_favorite)


@router.post(
    "/feed/{item_id}/ask", response_model=AskResponse, summary="Задать вопрос (заглушка AI)"
)
def ask(item_id: str, body: AskRequest, request: Request, user: CurrentUser) -> AskResponse:
    item = find_item(request.app.state.store, item_id, user)
    return AskResponse(
        feed_item_id=item.id,
        answer=answer_news_question(item.news, item.insight, body.question),
    )

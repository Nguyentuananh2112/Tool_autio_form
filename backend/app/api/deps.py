"""Dependency Injection dùng chung cho các router."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import TOKEN_HEADER, is_token_valid

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def require_app_token(x_app_token: Annotated[str | None, Header(alias=TOKEN_HEADER)] = None) -> None:
    if not is_token_valid(get_settings(), x_app_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Thiếu hoặc sai mã ứng dụng."})


def get_runner_kwargs(request: Request) -> dict[str, Any]:
    """Tham số cho CampaignRunner (test thay bằng submitter giả, tránh gửi thật lên Google)."""
    return dict(getattr(request.app.state, "runner_kwargs", {}))


RunnerKwargs = Annotated[dict[str, Any], Depends(get_runner_kwargs)]

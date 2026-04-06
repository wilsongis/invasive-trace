"""Dashboard routes for the HITL review interface."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the HITL dashboard with Leaflet map and HTMX sidebar."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

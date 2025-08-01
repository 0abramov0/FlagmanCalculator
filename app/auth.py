from fastapi import APIRouter, Request, Form, Response, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from .dependencies import get_current_user, create_session, delete_session, authenticate_user
from .database import init_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.on_event("startup")
async def startup_event():
    init_db()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def perform_login(
        request: Request,
        response: Response,
        username: str = Form(...),
        password: str = Form(...)
):
    username = username.strip()
    password = password.strip()

    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверные учетные данные"},
            status_code=401
        )

    session_id = create_session(username)

    redirect = RedirectResponse("/", status_code=302)
    redirect.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=3600
    )
    return redirect


@router.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id)

    redirect = RedirectResponse("/login", status_code=302)
    redirect.delete_cookie("session_id")
    return redirect

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from .dependencies import get_current_user, is_admin
from .database import get_all_users, add_user, delete_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    user = get_current_user(request)
    if not user or not is_admin(user):
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    users = get_all_users()
    users_list = [dict(user) for user in users]

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "users": users_list,
            "current_user": user["username"]
        }
    )


@router.post("/admin/add-user")
async def add_user_view(
        request: Request,
        username: str = Form(...),
        password: str = Form(...)
):
    user = get_current_user(request)
    if not user or not is_admin(user):
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    username = username.strip()
    if not username:
        return RedirectResponse("/admin?error=Имя пользователя не может быть пустым", status_code=302)

    if not add_user(username, password):
        return RedirectResponse("/admin?error=Пользователь уже существует", status_code=302)

    return RedirectResponse("/admin?success=Пользователь добавлен", status_code=302)


@router.post("/admin/delete-user")
async def delete_user_view(
        request: Request,
        username: str = Form(...)
):
    user = get_current_user(request)
    if not user or not is_admin(user):
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    if username == user["username"]:
        return RedirectResponse("/admin?error=Нельзя удалить себя", status_code=302)

    if not delete_user(username):
        return RedirectResponse("/admin?error=Пользователь не найден", status_code=302)

    return RedirectResponse("/admin?success=Пользователь удален", status_code=302)
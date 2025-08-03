import json

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from .dependencies import get_current_user, is_admin
from .database import get_all_products, get_product, add_product, delete_product, get_products_by_category, get_category_by_name, get_product_categories, get_all_categories

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    products = get_all_products()
    products_list = [dict(product) for product in products]

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "products": products_list,
            "is_admin": is_admin(user),
            "get_product_categories": get_product_categories, # Добавляем функцию в контекст
            "get_all_categories": get_all_categories  # Добавляем функцию получения всех категорий
        }
    )


@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_page(request: Request, product_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    return templates.TemplateResponse(
        "product.html",
        {
            "request": request,
            "product": dict(product),
            "form_config": product["form_config"]
        }
    )


@router.post("/add-product")
async def add_product_view(
        request: Request,
        name: str = Form(...),
        description: str = Form(...),
        price: float = Form(0.0),
        form_config: str = Form(None),
        categories: str = Form("")
):
    user = get_current_user(request)
    if not user or not is_admin(user):
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    category_list = [c.strip() for c in categories.split(",") if c.strip()]
    print(f"Adding product with categories: {category_list}")

    if not name or price < 0:
        return RedirectResponse("/?error=Некорректные данные товара", status_code=302)

    form_config_obj = {}  # По умолчанию пустой словарь
    if form_config and form_config != "null":
        try:
            form_config_obj = json.loads(form_config)
            # Обрабатываем таблицы
            for field in form_config_obj:
                if field.get('type') == 'table' and 'allow_no_selection' not in field:
                    field['allow_no_selection'] = False
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования form_config: {e}")
            return RedirectResponse("/?error=Ошибка в конфигурации формы", status_code=302)

    product_id = add_product(name, description, price, form_config_obj, category_list)
    print(f"Result of add_product: {product_id}")

    if not product_id:
        return RedirectResponse("/?error=Ошибка при добавлении товара", status_code=302)
    return RedirectResponse("/?success=Товар добавлен", status_code=302)


@router.post("/delete-product")
async def delete_product_view(
        request: Request,
        product_id: int = Form(...)
):
    user = get_current_user(request)
    if not user or not is_admin(user):
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    if not delete_product(product_id):
        return RedirectResponse("/?error=Товар не найден", status_code=302)

    return RedirectResponse("/?success=Товар удален", status_code=302)


@router.get("/form-builder", response_class=HTMLResponse)
async def form_builder(request: Request):
    user = get_current_user(request)
    if not user or not is_admin(user):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return templates.TemplateResponse("form-builder.html", {"request": request})

@router.get("/category/{category_name}", response_class=HTMLResponse)
async def category_page(request: Request, category_name: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    category = get_category_by_name(category_name)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    products = get_products_by_category(category['id'])
    products_list = [dict(product) for product in products]

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "products": products_list,
            "is_admin": is_admin(user),
            "get_product_categories": get_product_categories,
            "get_all_categories": get_all_categories,
            "current_category": category['name']  # Добавляем текущую категорию в контекст
        }
    )


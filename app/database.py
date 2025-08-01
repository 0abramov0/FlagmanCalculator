import json
import sqlite3
import bcrypt
from contextlib import contextmanager

DATABASE = "app.db"


def init_db():
    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user'
                )
                """)

        cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    form_config TEXT,
                    price REAL NOT NULL DEFAULT 0.0
                )
                """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_categories (
            product_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (product_id, category_id),
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
        """)

        admin_username = "admin"
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (admin_username,))
        if cursor.fetchone()[0] == 0:
            admin_password = "aFC#15N3"
            hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (admin_username, hashed_password, "admin")
            )
        conn.commit()


@contextmanager
def db_connection():
    conn = sqlite3.connect(DATABASE, timeout=30.0)  # Увеличиваем таймаут
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Включаем режим WAL
    try:
        yield conn
    finally:
        conn.close()


def get_user(username: str):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()


def get_all_users():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()


def add_user(username: str, password: str, role: str = "user"):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hashed_password, role)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def delete_user(username: str):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return cursor.rowcount > 0


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)


def get_all_products():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT *, price FROM products ORDER BY created_at DESC")
        return cursor.fetchall()


def get_product(product_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if product:
            product = dict(product)
            # Правильно обрабатываем form_config
            if product.get("form_config"):
                try:
                    # Декодируем JSON строку в объект Python
                    product["form_config"] = json.loads(product["form_config"])
                except json.JSONDecodeError:
                    product["form_config"] = None
            else:
                product["form_config"] = None
        return product


def add_product(name: str, description: str, price: float = 0.0, form_config: dict = None, categories: list = None):
    if form_config:
        # Проверяем, есть ли уже поле "Количество" в конфигурации
        has_quantity = any(field.get('name') == 'quantity' for field in form_config)

        if not has_quantity:
            # Добавляем поле "Количество" только если его нет
            quantity_field = {
                'type': 'number',
                'label': 'Количество',
                'name': 'quantity',
                'min': 1,
                'max': 1000000,
                'default': 1,
                'price_mod': 0
            }
            form_config.insert(0, quantity_field)

    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            form_config_json = json.dumps(form_config, ensure_ascii=False) if form_config else None

            # Начинаем транзакцию
            conn.execute("BEGIN TRANSACTION")

            # Добавляем товар
            cursor.execute(
                "INSERT INTO products (name, description, price, form_config) VALUES (?, ?, ?, ?)",
                (name, description, price, form_config_json)
            )
            product_id = cursor.lastrowid

            # Добавляем категории
            if categories:
                for category_name in categories:
                    # Проверяем существование категории
                    category = get_category_by_name(category_name)
                    if not category:
                        # Создаем новую категорию, если не существует
                        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
                        category_id = cursor.lastrowid
                    else:
                        category_id = category['id']

                    # Связываем товар с категорией
                    cursor.execute(
                        "INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)",
                        (product_id, category_id)
                    )

            # Фиксируем транзакцию
            conn.commit()
            return product_id
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            conn.rollback()  # Откатываем транзакцию при ошибке
            return None


def delete_product(product_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_categories():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        return cursor.fetchall()

def get_category_by_name(name: str):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
        return cursor.fetchone()

def add_category(name: str):
    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

def add_product_to_category(product_id: int, category_id: int):
    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)",
                (product_id, category_id)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_products_by_category(category_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.* FROM products p
            JOIN product_categories pc ON p.id = pc.product_id
            WHERE pc.category_id = ?
            ORDER BY p.created_at DESC
        """, (category_id,))
        return cursor.fetchall()

def get_product_categories(product_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.* FROM categories c
            JOIN product_categories pc ON c.id = pc.category_id
            WHERE pc.product_id = ?
        """, (product_id,))
        return cursor.fetchall()

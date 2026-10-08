import sqlite3
import pandas as pd

def get_connection():
    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def pd_connection():
    conn = sqlite3.connect("store.db")
    pd_customers = pd.read_sql("SELECT * FROM customers", conn)
    pd_products = pd.read_sql("SELECT * FROM products", conn)
    pd_orders = pd.read_sql("SELECT * FROM orders", conn)
    pd_order_products = pd.read_sql("SELECT * FROM order_products", conn)

def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            visits INTEGER NOT NULL DEFAULT 0,
            loyalty_rank TEXT DEFAULT "BRONZE",
            joined TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,
            price INTEGER NOT NULL CHECK (price >= 0),
            stock INTEGER NOT NULL CHECK (stock >= 0)
        )
        """)

        conn.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            created TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.execute("""CREATE TABLE IF NOT EXISTS order_products (
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price REAL NOT NULL CHECK (unit_price > 0),
            PRIMARY KEY (order_id, product_id)
        )
        """)

        cols = [row["name"] for row in  conn.execute("PRAGMA table_info(products)")]
        if "category" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN category TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_order_products_product ON order_products(product_id)")


def seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        with conn:
            conn.executemany("INSERT INTO products (product, price, stock) VALUES (?,?,?)",
                            [
                            ("NOTEBOOK", 45, 6),
                                ("PEN", 10, 15),
                                ("COVER", 5, 12),
                                ("BAGPACK", 250, 3),
                            ]
                            )
        
            conn.execute("UPDATE products SET category = 'stationery' WHERE product IN ('NOTEBOOK','PEN','COVER')")
            conn.execute("UPDATE products SET category = 'bags' WHERE product = 'BAGPACK'")
    conn.close()

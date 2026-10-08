from fastapi import FastAPI, HTTPException
import database
from schemas import Products, Post_Products, Customers, Post_Customers, OrderItemCreate, OrderCreate
from typing import Optional, Annotated
from datetime import datetime
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

database.init_db()

app = FastAPI()

database.seed_data()

@app.get("/")
def health():
    return {"status": "working", "store": "open"}

@app.get("/products")
def get_products(max_price: Optional[float] = None,
                 category: Optional[str] = None,
                 limit: int = 10,
                 offset: int = 0,
                 ) -> list[Products]:
    conn = database.get_connection()
    query = "SELECT * FROM products"
    conditions = []
    params = []
    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)
    if category is not None:
        conditions.append("category = ?")
        params.append(category)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " LIMIT ? OFFSET ?"
    params.append(limit)
    params.append(offset)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/products/expensive")
def get_expensive():
    conn = database.get_connection()
    cursor = conn.cursor()
    expensive = cursor.execute("""SELECT products.id, products.product, products.price, products.stock
                FROM products
                WHERE price > (SELECT AVG(price) FROM products)
                ORDER BY price DESC""").fetchall()
    avg = cursor.execute("SELECT AVG(price) AS avg_price FROM products").fetchone()["avg_price"]
    conn.close()
    return {
        "avg": avg,
        "above average": [dict(row) for row in expensive]
    }
    

@app.get("/products/deadstock")
def get_deadstock():
    conn = database.get_connection()
    cursor = conn.cursor()
    deadstock = cursor.execute("""SELECT products.id, products.product, products.price, products.stock 
                FROM products 
                LEFT JOIN order_products
                ON order_products.product_id = products.id
                WHERE order_products.product_id IS NULL""").fetchall()
    conn.close()
    return [dict(row) for row in deadstock]

@app.get("/customers/inactive")
def inactive_customers():
    conn = database.get_connection()
    cursor = conn.cursor()
    inactive_customers = cursor.execute("""SELECT customers.id, customers.name, customers.email, customers.joined 
                    FROM customers 
                    LEFT JOIN orders
                    ON customers.id = orders.customer_id
                    WHERE orders.customer_id IS NULL""").fetchall()
    conn.close()
    return [dict(row) for row in inactive_customers]
    

@app.post("/products")
def post_products(product: Post_Products) -> Products:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (product, price, stock) VALUES (?,?,?) ", (product.product, product.price, product.stock))
    new_id = cursor.lastrowid
    row = cursor.execute("SELECT * FROM products WHERE id = ?", (new_id,)).fetchone()
    conn.commit()
    conn.close()
    return dict(row)

@app.get("/customers")
def get_customers() -> list[Customers]:
    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM customers").fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/customers/{customer_id}/orders")
def get_customer_orders(customer_id: int):
    conn = database.get_connection()
    cursor = conn.cursor()
    customer = conn.execute("SELECT name FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if customer is None:
        conn.close()
        raise HTTPException(status_code = 404, detail="Order not found")
    
    rows = cursor.execute("""SELECT orders.id, orders.created, COUNT(order_products.product_id) AS item_count, SUM(order_products.quantity * order_products.unit_price) AS total FROM orders JOIN order_products ON order_products.order_id = orders.id WHERE orders.customer_id = ? GROUP BY orders.id
    """, (customer_id, )).fetchall()
    conn.close()

    orders = [dict(row) for row in rows]
    lifetime_value = sum(row["total"] for row in rows)            

    return {
        "customer": customer["name"],
        "orders": orders,
        "order_count": len(orders),
        "lifetime_value": lifetime_value
    }

@app.post("/customers")
def post_customers(customer: Post_Customers) -> Customers:
    conn = database.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO customers (name, email) VALUES (?,?)", (customer.name, customer.email))
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code = 409, detail = "Email already in use")
    new_id = cursor.lastrowid
    row = cursor.execute("SELECT * FROM customers WHERE id = ?",(new_id,)).fetchone()
    conn.commit()
    conn.close()
    return dict(row)

@app.post("/order")
def create_order(order: OrderCreate):
    conn = database.get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (customer_id) VALUES (?)", (order.customer_id,))
        order_id = cursor.lastrowid
        for item in order.items:
            product = cursor.execute("SELECT price, stock FROM products WHERE id = ?", (item.product_id,)).fetchone()
            unit_price = product["price"]
            stock = product["stock"]
            if stock >= item.quantity:
                cursor.execute("INSERT INTO order_products (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)", (order_id, item.product_id, item.quantity, unit_price))
                new_stock = stock - item.quantity
                cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, item.product_id))
            else:
                raise HTTPException(status_code=400, detail=f"Not enough stock for product {item.product_id}")

    conn.close()
    return {"order": order_id, "status": "created"}


@app.get("/orders")
def get_order():
    conn = database.get_connection()

    orders = conn.execute("""SELECT orders.id, orders.created, customers.name AS customer_name
                    FROM orders
                    JOIN customers ON orders.customer_id = customers.id""").fetchall()
    conn.close()
    return [dict(order) for order in orders]

@app.get("/orders/{order_id}")
def get_order_id(order_id: int):
    conn = database.get_connection()

    order = conn.execute("""
        SELECT orders.id, orders.created, customers.name AS customer_name
        FROM orders
        JOIN customers ON orders.customer_id = customers.id
        WHERE orders.id = ?
    """, (order_id,)).fetchone()

    if order is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    products = conn.execute("""
        SELECT products.product, order_products.quantity, order_products.unit_price
        FROM order_products
        JOIN products ON order_products.product_id = products.id
        WHERE order_products.order_id = ?
    """, (order_id,)).fetchall()

    conn.close()

    items = []
    total = 0
    for row in products:
        line_total = row["unit_price"] * row["quantity"]
        total += line_total
        items.append({
            "product": row["product"],
            "quantity": row["quantity"],
            "unit_price": row["unit_price"],
            "line_total": line_total
        })

    return {
        "order_id": order["id"],
        "created": order["created"],
        "customer": order["customer_name"],
        "items": items,
        "total": total
    }

@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    conn = database.get_connection()
    order = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    item_count = conn.execute("SELECT COUNT(*) AS count FROM order_products WHERE order_id = ?",(order_id,)).fetchone()["count"]
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return {"deleted_order": order_id, "items_removed": item_count}
    


@app.get("/stats")
def get_stats():
    conn = database.get_connection()
    cursor = conn.cursor()
    revenue = cursor.execute("""SELECT products.product,
            SUM(order_products.quantity) AS units_sold,
            SUM(order_products.quantity * order_products.unit_price) AS revenue
            FROM order_products
            JOIN products ON order_products.product_id = products.id
            GROUP BY products.id
            ORDER BY revenue DESC""").fetchall()
    best_seller = cursor.execute("""SELECT products.product, SUM(order_products.quantity) AS units_sold
            FROM order_products
            JOIN products ON order_products.product_id = products.id
            GROUP BY products.id
            ORDER BY units_sold DESC
            LIMIT 1""").fetchone()
    top_customers = cursor.execute("""SELECT customers.name,
            COUNT(DISTINCT orders.id) AS order_count,
            SUM(order_products.quantity * order_products.unit_price) AS total_spent
            FROM customers
            JOIN orders ON orders.customer_id = customers.id
            JOIN order_products ON order_products.order_id = orders.id
            GROUP BY customers.id
            HAVING total_spent > 200
            ORDER BY total_spent DESC""")

    return {
    "revenue_by_product": [dict(row) for row in revenue],
    "best_seller": dict(best_seller) if best_seller else None,
    "top_customers": [dict(row) for row in top_customers]
}

@app.get("/stats/pd")
def stats_pd():
    conn = sqlite3.connect("store.db")
    pd_customers = pd.read_sql("SELECT * FROM customers", conn)
    pd_products = pd.read_sql("SELECT * FROM products", conn)
    pd_orders = pd.read_sql("SELECT * FROM orders", conn)
    pd_order_products = pd.read_sql("SELECT * FROM order_products", conn)
    merged_products = pd.merge(pd_order_products, pd_products, left_on = "product_id", right_on = "id")
    merged_products["line_total"] = merged_products["unit_price"] * merged_products["quantity"]
    revenue = merged_products.groupby("product")["line_total"].sum()
    revenue = revenue.sort_values(ascending = False)

    merged_customers = pd.merge(pd_orders, pd_order_products, left_on = "id", right_on = "order_id")
    merged_customers = pd.merge(merged_customers, pd_customers, left_on = "customer_id", right_on = "id")
    merged_customers["line_total"] = merged_customers["quantity"] * merged_customers["unit_price"]
    top_customer = merged_customers.groupby("name")["line_total"].sum()
    top_customer = top_customer.sort_values(ascending = False)
    top_customer = top_customer[top_customer > 200]
    return {
        "revenue by product": revenue.to_dict(),
        "top customer": top_customer.to_dict()
        }
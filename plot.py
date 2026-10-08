import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

conn = sqlite3.connect("store.db")
products = pd.read_sql("SELECT * FROM products", conn)
order_products = pd.read_sql("SELECT * FROM order_products", conn)
conn.close()

merged = pd.merge(order_products, products, left_on="product_id", right_on="id")
merged["line_total"] = merged["unit_price"] * merged["quantity"]
revenue = merged.groupby("product")["line_total"].sum().sort_values(ascending=False)

print(revenue)

revenue.plot(kind="bar", title="Revenue by Product")
plt.ylabel("Revenue ($)")
plt.tight_layout()
plt.show()
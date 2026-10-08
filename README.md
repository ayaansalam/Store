# store

Small online store backend made with FastAPI, Pydantic and SQLite. Has products, customers and orders, with stock checking and sales stats.

Features:
- **Products:** add, list, filter by price and category, pagination
- **Customers:** add and list, duplicate emails blocked (409)
- **Orders:** place orders with stock check, whole order cancels if anything is out of stock
- **Order details:** items, line totals and order total using joins
- **Order history:** every order for a customer with totals
- **Delete orders:** order items are removed automatically (cascade)
- **Stats:** revenue per product, best seller and top customers
- **Reports:** products never sold, customers with no orders, above average priced products
- **Pandas version:** same stats done with pandas, plus a revenue chart in plot.py

To run:
```
pip install fastapi uvicorn pandas matplotlib
uvicorn store:app --reload
```

http://127.0.0.1:8000/docs

from pydantic import BaseModel
from typing import Optional

class Post_Products(BaseModel):
    product: str
    price: int
    stock: int

class Products(Post_Products):
    id: int
    category: Optional[str] = None

class Post_Customers(BaseModel):
    name: str
    email: str

class Customers(Post_Customers):
    id: int
    visits: int
    loyalty_rank: str
    joined: str

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate]

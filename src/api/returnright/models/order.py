"""Orders (order number, customer, delivery date, payment method) and order items.

The customer's email lives on customers; an order is matched to an email through customer_id.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from returnright.models.base import Base
from returnright.models.catalog import Product
from returnright.models.customer import Customer


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    payment_method: Mapped[str] = mapped_column(String(20))
    ordered_at: Mapped[datetime]
    delivered_at: Mapped[datetime | None]
    total_amount: Mapped[Decimal]

    customer: Mapped[Customer] = relationship(lazy="raise")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", lazy="raise", order_by="OrderItem.order_item_id"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[int] = mapped_column(SmallInteger)
    unit_price: Mapped[Decimal]  # price at time of purchase

    order: Mapped[Order] = relationship(back_populates="items", lazy="raise")
    product: Mapped[Product] = relationship(lazy="raise")

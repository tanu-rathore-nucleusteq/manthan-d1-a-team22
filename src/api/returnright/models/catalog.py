"""Categories (return window in days, returnable or not) and products."""

from decimal import Decimal

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from returnright.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    is_returnable: Mapped[bool] = mapped_column(default=True)
    return_window_days: Mapped[int | None] = mapped_column(SmallInteger)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    category_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("categories.category_id"))
    price: Mapped[Decimal]

    category: Mapped[Category] = relationship(lazy="raise")

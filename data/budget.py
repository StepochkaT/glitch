from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime

from data.db_session import SqlAlchemyBase


class Budget(SqlAlchemyBase):
    __tablename__ = 'budgets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    planned_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
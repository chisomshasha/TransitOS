"""Expense request/response schemas."""

from app.models.expense import Expense, ExpenseCreate, ExpenseUpdate


class ExpenseCreateRequest(ExpenseCreate):
    pass


class ExpenseUpdateRequest(ExpenseUpdate):
    pass


class ExpenseResponse(Expense):
    pass

from transactions.views import (
    DepositMoneyView,
    WithdrawMoneyView,
    TransactionReportView,
)
from django.urls import path

app_name = "transactions"


urlpatterns = [
    path("deposit/", DepositMoneyView.as_view(), name="deposit_money"),
    path("report/", TransactionReportView.as_view(), name="transaction_report"),
    path("withdraw/", WithdrawMoneyView.as_view(), name="withdraw_money"),
]

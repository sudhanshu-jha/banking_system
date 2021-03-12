from django.shortcuts import render
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView
from transactions.choices import DEPOSIT, WITHDRAWAL
from transactions.forms import (
    DepositForm,
    TransactionDateRangeForm,
    WithdrawForm,
)
from transactions.models import Transaction
import xlwt
from django.http import HttpResponse
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = "transactions/transaction_report.html"
    model = Transaction
    form_data = {}

    def get(self, request, *args, **kwargs):
        form = TransactionDateRangeForm(request.GET or None)
        if form.is_valid():
            self.form_data = form.cleaned_data

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().filter(account=self.request.user.account)

        daterange = self.form_data.get("daterange")

        if daterange:
            queryset = queryset.filter(timestamp__date__range=daterange)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "account": self.request.user.account,
                "form": TransactionDateRangeForm(self.request.GET or None),
            }
        )

        return context


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = "transactions/transaction_form.html"
    model = Transaction
    title = ""
    success_url = reverse_lazy("transactions:transaction_report")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"account": self.request.user.account})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": self.title})

        return context


class DepositMoneyView(TransactionCreateMixin):

    form_class = DepositForm
    title = "Deposit Money to Your Account"

    def get_initial(self):
        initial = {"transaction_type": DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get("amount")
        account = self.request.user.account

        if not account.initial_deposit_date:
            now = timezone.now()
            next_interest_month = int(
                12 / account.account_type.interest_calculation_per_year
            )
            account.initial_deposit_date = now
            account.interest_start_date = now + relativedelta(
                months=+next_interest_month
            )

        account.balance += amount
        account.save(
            update_fields=["initial_deposit_date", "balance", "interest_start_date"]
        )

        messages.success(
            self.request, f"{amount}$ was deposited to your account successfully"
        )

        send_mail(
            "Amount Credited",
            "Rs."
            + str(amount)
            + "amount  was deposited to your account successfully to account"
            + str(account),
            "emaildemon19@gmail.com",
            [str(self.request.user)],
            fail_silently=False,
        )

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = "Withdraw Money from Your Account"

    def get_initial(self):
        initial = {"transaction_type": WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get("amount")
        account = self.request.user.account

        account.balance -= form.cleaned_data.get("amount")
        account.save(update_fields=["balance"])

        messages.success(
            self.request, f"Successfully withdrawn {amount}$ from your account"
        )

        send_mail(
            "Amount Withdrawl",
            "Rs."
            + str(amount)
            + "amount  was withdrawl from your account"
            + str(account)
            + "successfully ",
            "emaildemon19@gmail.com",
            [str(self.request.user)],
            fail_silently=False,
        )

        return super().form_valid(form)


def download_excel_data(request):
    response = HttpResponse(content_type="application/ms-excel")

    response["Content-Disposition"] = 'attachment; filename="report.xls"'

    wb = xlwt.Workbook(encoding="utf-8")

    ws = wb.add_sheet("sheet1")

    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ["Name", "Transaction Type", "Date", "Amount"]

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    data = get_data()
    for my_row in data:
        row_num = row_num + 1
        ws.write(row_num, 0, my_row.name, font_style)
        ws.write(row_num, 1, my_row.start_date_time, font_style)
        ws.write(row_num, 2, my_row.end_date_time, font_style)
        ws.write(row_num, 3, my_row.notes, font_style)

    wb.save(response)
    return response

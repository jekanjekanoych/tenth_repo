import datetime
import decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render

from .models import Rate
from .forms import ExchangeForm


class DecimalAsFloatJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)


def best_rate(date, currency, operation):
    rates = (
        Rate.objects.exclude(vendor="govua")
        .filter(date=date, currency_a=currency)
        .all()
        .values()
    )
    if operation == "sell":
        return rates.order_by("sell").last()
    elif operation == "buy":
        return rates.order_by("buy").first()


def index(request):
    if request.method == "POST":
        form = ExchangeForm(request.POST)
        if form.is_valid():
            currency_value = form.cleaned_data["currency_value"]
            operation = form.cleaned_data["operation"]
            currency = form.cleaned_data["currency"]
            current_date = datetime.date.today()

            best = best_rate(current_date, currency, operation)
            result = best[operation] * currency_value

            context = {
                "form": form,
                "result": result,
                "best_rate_value": best[operation],
                "best_vendor": best["vendor"],
                "best_rate_date": best["date"],
                "operation": operation,
            }
            return render(request, "index.html", context)
    else:
        form = ExchangeForm()
    return render(request, "index.html", {"form": form})


def rates(request):
    current_date = datetime.date.today()
    current_rates = Rate.objects.filter(date=current_date).all().values()
    return JsonResponse(
        {"current_rates": list(current_rates)}, encoder=DecimalAsFloatJSONEncoder
    )

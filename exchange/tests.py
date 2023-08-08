import json
import pathlib

import pytest
import responses
from django.core.management import call_command
from freezegun import freeze_time
from django.test.client import RequestFactory
from .exchange_provider import (
    MonoExchange,
    PrivatExchange,
    VkurseExchange,
    GovUaExchange,
    MinfinExchange,
)
from .views import index, best_rate, rates

root = pathlib.Path(__file__).parent


@pytest.fixture
def mocked():
    def inner(file_name):
        return json.load(
            open(root / "fixtures" / file_name, encoding="utf-8", mode="r")
        )

    return inner


@responses.activate
def test_exchange_mono(mocked):
    mocked_response = mocked("mono_response.json")
    responses.get(
        "https://api.monobank.ua/bank/currency",
        json=mocked_response,
    )
    e = MonoExchange("mono", "USD", "UAH")
    e.get_rate()
    assert e.pair.sell == 37.4406


@responses.activate
def test_privat_rate(mocked):
    mocked_response = mocked("privat_response.json")
    responses.get(
        "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=11",
        json=mocked_response,
    )
    e = PrivatExchange("privat", "USD", "UAH")
    e.get_rate()
    assert e.pair.sell == 37.45318


@responses.activate
def test_vkurse(mocked):
    mocked_response = mocked("vkurse_response.json")
    responses.get(
        "https://vkurse.dp.ua/course.json",
        json=mocked_response,
    )
    e = VkurseExchange("vkurse", "USD", "UAH")
    e.get_rate()
    assert e.pair.sell == 37.3


@responses.activate
def test_govua(mocked):
    mocked_response = mocked("bank_gov_ua_response.json")
    responses.get(
        "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json",
        json=mocked_response,
    )
    e = GovUaExchange("govua", "USD", "UAH")
    e.get_rate()
    assert e.pair.sell == 36.5686


@responses.activate
def test_minfin(mocked):
    mocked_response = mocked("minfin_response.json")
    responses.get(
        "https://api.minfin.com.ua/summary/8b5b01d410dcd6306fdd953856806fcb53842041/",
        json=mocked_response,
    )
    e = MinfinExchange("minfin", "USD", "UAH")
    e.get_rate()
    assert e.pair.sell == 37.4000

    @pytest.fixture(scope="session")
    def django_db_setup(django_db_setup, django_db_blocker):
        with django_db_blocker.unblock():
            call_command("loaddata", "db_init.yaml")

    @freeze_time("2023-08-07")
    @pytest.mark.django_db
    def test_index_view():
        response = index(None)
        assert response.status_code == 200
        assert json.loads(response.content) == {
            "current_rates": [
                {
                    "id": 1,
                    "date": "2023-08-07",
                    "vendor": "mono",
                    "currency_a": "EUR",
                    "currency_b": "UAH",
                    "sell": 41.5507,
                    "buy": 40.25,
                },
                {
                    "id": 2,
                    "date": "2023-08-07",
                    "vendor": "privat",
                    "currency_a": "EUR",
                    "currency_b": "UAH",
                    "sell": 41.84100,
                    "buy": 40.00240,
                },
            ]
        }

    @freeze_time("2023-08-07")
    @pytest.mark.django_db
    def test_index_view_get():
        r = RequestFactory()
        request = r.get("")
        response = index(request)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_best_rate_sell():
        current_date = "2023-08-07"
        currency = "EUR"
        operation = "sell"
        best_rate = best_rate(current_date, currency, operation)
        assert float(best_rate[operation]) == 41.84100

    @pytest.mark.django_db
    def test_best_rate_buy():
        current_date = "2023-08-07"
        currency = "EUR"
        operation = "buy"
        best_rate = best_rate(current_date, currency, operation)
        assert float(best_rate[operation]) == 40.00240

    @freeze_time("2023-08-07")
    @pytest.mark.django_db
    def test_index_view_post_sell():
        r = RequestFactory()
        request = r.post(
            "",
            {
                "currency_value": "200",
                "operation": "sell",
                "currency": "EUR",
            },
        )
        response = index(request)
        assert response.status_code == 200

    @freeze_time("2023-08-07")
    @pytest.mark.django_db
    def test_index_view_post_buy():
        r = RequestFactory()
        request = r.post(
            "",
            {
                "currency_value": "300",
                "operation": "buy",
                "currency": "EUR",
            },
        )
        response = index(request)
        assert response.status_code == 200

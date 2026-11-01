"""Official statistics without keys: National Bank of Ukraine, National Bank
of Poland, Eurostat, and General Staff of the AFU losses data (via the open
russianwarship.rip API, which republishes the daily mil.gov.ua figures)."""

from datetime import date, timedelta
from typing import List

from ..http import FetchError, get_json
from ..models import Series


def nbu_fx(currency: str = "USD", days: int = 180) -> Series:
    end = date.today()
    start = end - timedelta(days=days)
    rows = get_json("https://bank.gov.ua/NBU_Exchange/exchange_site", params={
        "start": f"{start:%Y%m%d}", "end": f"{end:%Y%m%d}", "valcode": currency.lower(),
        "sort": "exchangedate", "order": "asc", "json": "",
    }, ttl=21600)
    if not rows:
        raise FetchError(f"nbu: no {currency} rates")
    dates = ["".join(reversed(r["exchangedate"].split("."))) for r in rows]
    return Series(f"NBU {currency}/UAH", "fx", dates, [float(r["rate_per_unit"]) for r in rows],
                  "UAH", "bank.gov.ua")


def nbu_key_rate(days: int = 365) -> Series:
    """NBU key policy rate, sampled monthly (the API answers per date)."""
    dates, values = [], []
    today = date.today()
    for back in range(0, days, 30):
        d = today - timedelta(days=back)
        rows = get_json("https://bank.gov.ua/NBUStatService/v1/statdirectory/key",
                        params={"date": f"{d:%Y%m%d}", "json": ""}, ttl=86400)
        rate = next((r["value"] for r in rows if r.get("id_api") == "KEY_PolicyRate"), None)
        if rate is not None:
            dates.append(f"{d:%Y%m%d}")
            values.append(float(rate))
    if not values:
        raise FetchError("nbu: key rate unavailable")
    return Series("NBU key rate", "rate", dates[::-1], values[::-1], "%", "bank.gov.ua")


def nbp_fx(currency: str = "EUR", days: int = 180) -> Series:
    data = get_json(f"https://api.nbp.pl/api/exchangerates/rates/a/{currency.lower()}/"
                    f"last/{min(days, 255)}/", params={"format": "json"}, ttl=21600)
    rates = data.get("rates", [])
    return Series(f"NBP {currency}/PLN", "fx", [r["effectiveDate"].replace("-", "") for r in rates],
                  [float(r["mid"]) for r in rates], "PLN", "nbp.pl")


def eurostat_hicp(geo: str = "PL", months: int = 36) -> Series:
    """Annual HICP inflation, monthly."""
    data = get_json("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
                    "prc_hicp_manr", params={"geo": geo, "coicop": "CP00",
                                             "lastTimePeriod": months}, ttl=86400)
    index = data["dimension"]["time"]["category"]["index"]
    values = data.get("value", {})
    points = sorted((period, float(values[str(pos)])) for period, pos in index.items()
                    if str(pos) in values)
    return Series(f"Eurostat HICP {geo}", "inflation", [p[0].replace("-", "") for p in points],
                  [p[1] for p in points], "% y/y", "eurostat")


WAR_FIELDS = {
    "personnel_units": "personnel", "tanks": "tanks", "artillery_systems": "artillery",
    "uav_systems": "drones", "cruise_missiles": "missiles", "vehicles_fuel_tanks": "vehicles",
}


def war_losses(days: int = 150) -> List[Series]:
    """Daily increase of enemy losses by category."""
    end = date.today()
    data = get_json("https://russianwarship.rip/api/v2/statistics", params={
        "date_from": f"{end - timedelta(days=days):%Y-%m-%d}", "date_to": f"{end:%Y-%m-%d}",
    }, ttl=10800)
    records = data.get("data", {}).get("records", [])
    if not records:
        raise FetchError("russianwarship: no records")
    dates = [r["date"].replace("-", "") for r in records]
    return [Series(f"Losses/day: {name}", "war_losses", dates,
                   [float(r["increase"].get(field, 0) or 0) for r in records], "units/day",
                   "mil.gov.ua via russianwarship.rip")
            for field, name in WAR_FIELDS.items()]

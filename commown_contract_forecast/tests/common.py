from datetime import date

from dateutil.relativedelta import relativedelta


def fake_today():
    """Forecast tests check contract forecasts' behaviour, which depends on the date
    when the tests are run. The problem is that contract recurring next date field is
    not that predictable as its behaviour at end of month dates is shaky.

    We circumvent this problem by choosing a date slightly in the past and not close to
    the end of a month.
    """
    base_date = date.today() - relativedelta(days=7)
    if base_date.day > 27:
        base_date = date(base_date.year, base_date.month, 27)
    return base_date

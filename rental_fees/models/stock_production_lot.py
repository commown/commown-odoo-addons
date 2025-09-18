from dateutil.relativedelta import relativedelta

from odoo import fields, models

_one_day = relativedelta(days=1)


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    def _single_device_rental_periods(self, to_date=None):
        today = fields.Date.today()
        if to_date is None:
            has_forecast = False
            to_date = today
        else:
            has_forecast = to_date > today
            if has_forecast:
                extend_until = to_date
                to_date = today

        current_period = {}
        result = []

        move_lines = (
            self.env["stock.move.line"]
            .search(
                [
                    ("state", "=", "done"),
                    ("lot_id", "=", self.id),
                    ("move_id.date", "<", to_date + _one_day),
                ]
            )
            .sorted(lambda ml: ml.move_id.date)
        )

        customer_locations = self.env["stock.location"].search(
            [("id", "child_of", self.env.ref("stock.stock_location_customers").id)]
        )

        for move_line in move_lines:
            move = move_line.move_id
            move_date = move.date.date()

            if move_line.location_dest_id in customer_locations:
                if not current_period:
                    current_period["is_forecast"] = False
                    current_period["from_date"] = move_date
                    current_period["contract"] = move.contract_id
                else:
                    raise ValueError(
                        "Device %s was already at customer location" % self.name
                    )

            elif current_period:
                assert (
                    move_line.location_id in customer_locations
                ), "Device %s should be moving to a customer at %s" % (
                    move_line.lot_id.name,
                    move_date,
                )
                current_period["to_date"] = move_date
                result.append(current_period.copy())
                current_period.clear()

        if current_period:
            current_period["to_date"] = to_date + _one_day
            result.append(current_period)

            if has_forecast:
                result.append(
                    dict(
                        current_period,
                        from_date=current_period["to_date"],
                        to_date=extend_until + _one_day,
                        is_forecast=True,
                    )
                )

        return result

    def rental_periods(self, to_date=None):
        """Return rental periods before given date for current resultset devices

        The returned value is a {stock.production.lot: [period]} dict
        where each period is a dict of the form:

        - contract: a contract.contract instance the device was attributed to
        - from_date: date from which the device was rented as of this contract
        - to_date: date to which the device was rented as of this contract
        """

        return {
            device: device._single_device_rental_periods(to_date) for device in self
        }

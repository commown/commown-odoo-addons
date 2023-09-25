from functools import partial

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date

from odoo.addons.queue_job.job import job


def _move_contract(move_line):
    "Helper to return the contract related to a device move"
    return move_line.move_id.picking_id.contract_id


def _not_canceled(invoice):
    "Helper to filter opened and paid invoices"
    return invoice.state != "cancel"


class RentalFeesComputation(models.Model):
    _name = "rental_fees.computation"
    _description = "Computation of rental fees"
    _inherit = ["mail.thread"]

    partner_id = fields.Many2one("res.partner", domain=[("is_company", "=", True)])

    fees_definition_ids = fields.Many2many(
        "rental_fees.definition",
        string="Fees definitions",
        required=True,
        domain='[("partner_id", "=", partner_id)]',
    )

    until_date = fields.Date(
        string="Compute until",
        help="Date until which fees are computed (past, present or future)",
        required=True,
        default=fields.Date.today,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("done", "Done"),
        ],
        "State",
        default="draft",
        index=True,
        readonly=True,
    )

    fees = fields.Float(
        string="Fees",
        copy=False,
    )

    detail_ids = fields.One2many(
        comodel_name="rental_fees.computation.detail",
        string="Computed fees details",
        inverse_name="fees_computation_id",
        ondelete="cascade",
        copy=False,
    )

    invoice_ids = fields.One2many(
        comodel_name="account.invoice",
        string="Invoice",
        inverse_name="fees_computation_id",
        help=(
            "The supplier invoices of the computed fees."
            " Generated from the invoice model defined on the fees definition."
        ),
        copy=False,
    )

    def details(self, *fees_types):
        return self.detail_ids.filtered(lambda d: d.fees_type in fees_types)

    def rental_details(self):
        return self.details("fees")

    def compensation_details(self):
        return self.details("no_rental_compensation", "lost_device_compensation")

    def per_device_revenues(self):
        fees_data = {
            item["lot_id"][0]: item["fees"]
            for item in self.env["rental_fees.computation.detail"].read_group(
                [("fees_computation_id", "=", self.id)],
                ["fees:sum"],
                ["lot_id"],
                lazy=False,
            )
        }

        purchase_data = {
            device: (fees_def, ol)
            for fees_def in self.fees_definition_ids
            for ol in fees_def.mapped("order_ids.order_line")
            for device in ol.mapped("move_ids.move_line_ids.lot_id")
        }

        result = {}

        for device in sorted(purchase_data, key=lambda d: d.product_id):
            fees_def, ol = purchase_data[device]
            price_ratio = fees_def.agreed_to_std_price_ratio
            purchase_price = ol.price_unit

            fees = fees_data.get(device.id, 0.0)
            result[device] = {
                "purchase": purchase_data[device].order_id,
                "purchase_line": purchase_data[device],
                "purchase_price": purchase_price,
                "without_agreement": purchase_price / price_ratio,
                "fees": fees,
                "total": purchase_price + fees,
            }
        return result

    def _has_later_invoiced_computation(self):
        self.ensure_one()
        return bool(
            self.search(
                [
                    ("until_date", ">", self.until_date),
                    ("fees_definition_ids", "in", self.fees_definition_ids.ids),
                    ("invoice_ids.state", "!=", "cancel"),
                ]
            )
        )

    @api.constrains("invoice_ids")
    def _check_future_invoices(self):
        for record in self:
            if record._has_later_invoiced_computation():
                raise ValidationError(
                    _(
                        "Operation not allowed: there are later fees"
                        " computations with invoices which amount would"
                        " become invalid."
                    )
                )

    def name_get(self):
        result = []
        for record in self:
            name = "%s (%s)" % (
                record.partner_id.name,
                format_date(self.env, record.until_date),
            )
            result.append((record.id, name))
        return result

    def rental_periods(self, device):
        """Return a descr of the rental periods of `device` until `self.date`

        Each period is a dict of the form:
        - contract: a contract.contract instance the device was attributed to
        - from_date: date from which the device was rented as of this contract
        - to_date: date to which the device was rented as of this contract
        """
        current_period = {}
        result = []

        move_lines = (
            self.env["stock.move.line"]
            .search(
                [
                    ("state", "=", "done"),
                    ("lot_id", "=", device.id),
                    ("move_id.date", "<=", self.until_date),
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
                    current_period["from_date"] = move_date
                    current_period["contract"] = move.picking_id.contract_id
                else:
                    raise ValueError("Device was already at customer location")

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
            current_period["to_date"] = self.until_date
            result.append(current_period)

        return result

    def scan_no_rental(self, fees_def, device, delivery_date, periods):
        """Scan gaps between periods for too long no rental periods

        Also mind the gap between the last period and the computation date, if any.
        Any rental period after the compensation is removed (would generate no fees).
        Returns the no rental date limit if reached (False otherwise), and the new
        rental period list.
        """

        if not periods:
            return False, periods

        no_rental_limit, result = False, [periods[0]]

        for period in periods[1:] + [{"fake": True, "from_date": self.until_date}]:
            last_rental_date = result[-1]["to_date"] or self.until_date
            no_rental_limit = self.valid_no_rental_limit(
                fees_def, delivery_date, last_rental_date, period["from_date"]
            )
            if no_rental_limit:
                break
            if not period.get("fake"):
                result.append(period)

        return no_rental_limit, result

    def _fees_def_split_dates(self, fees_def, origin_date):
        """Return the end dates defined by all fees def line from given origin_date

        The result is a {date: definition_line} dict
        """
        split_dates = {}

        for line in fees_def.line_ids:
            new_date = line.compute_end_date(origin_date)
            split_dates[new_date] = line
            origin_date = new_date

        return split_dates

    def split_periods_wrt_fees_def(self, fees_def, periods):
        """Split given periods into smaller ones wrt. given fees def

        ... and add the corresponding line definition to the resulting
        periods. Each given fees definition line defines a period on
        which the amount of the fees is uniform.
        """
        result = []

        split_dates = self._fees_def_split_dates(fees_def, periods[0]["from_date"])

        for period in periods:
            for split_date, fees_def_line in split_dates.items():

                if split_date and split_date < period["from_date"]:
                    continue

                from_date = (
                    max(result[-1]["to_date"], period["from_date"])
                    if result
                    else period["from_date"]
                )

                if split_date and split_date < period["to_date"]:
                    result.append(
                        {
                            "contract": period["contract"],
                            "from_date": from_date,
                            "to_date": split_date,
                            "fees_def_line": fees_def_line,
                        }
                    )

                else:
                    result.append(
                        {
                            "contract": period["contract"],
                            "from_date": from_date,
                            "to_date": period["to_date"],
                            "fees_def_line": fees_def_line,
                        }
                    )
                    break

        return result

    def valid_no_rental_limit(
        self, fees_def, delivery_date, last_rental_date, new_rental_date=None
    ):
        period_duration = relativedelta(years=fees_def.penalty_period_duration)
        no_rental_duration = relativedelta(months=fees_def.no_rental_duration)

        penalty_period_end = delivery_date + period_duration
        no_rental_limit = last_rental_date + no_rental_duration
        new_rental_date = new_rental_date or self.until_date

        if no_rental_limit <= new_rental_date and no_rental_limit <= penalty_period_end:
            return no_rental_limit

    def amounts_to_be_invoiced(self):
        "Return the amount to be invoiced for each fees def of present computation"

        def filter_by_def(fees_def, detail):
            return detail.fees_definition_id == fees_def

        details = self.detail_ids
        return {
            fees_def: (
                sum(details.filtered(partial(filter_by_def, fees_def)).mapped("fees"))
                - sum(fees_def.invoice_line_ids.mapped("price_subtotal"))
            )
            for fees_def in self.fees_definition_ids
        }

    @api.multi
    def action_invoice(self):
        """Generate a draft invoice based on the invoice model of the fees def

        The amount of this invoice is equal to the total fees minus the already
        invoiced fees (open and paid invoices of the same fees definition).

        Note that a user error is raised when there exists another computation
        for the same fees_def with an invoice which date is later than current
        computation's `until_date`.
        """
        self.ensure_one()

        inv, inv_line_name = None, None
        until_date = format_date(self.env, self.until_date)

        for fees_def, amount in self.amounts_to_be_invoiced().items():

            if self._has_later_invoiced_computation():
                raise UserError(
                    _("There is a later invoice for the same fees definition")
                )

            if not fees_def.model_invoice_id:
                raise UserError(
                    _("Please set the invoice model on the fees definition."),
                )

            inv_line_name = fees_def.model_invoice_id.invoice_line_ids[0].name
            markers = {"##DATE##": until_date, "##FEES_DEF##": fees_def.name}
            for marker, value in markers.items():
                if marker in inv_line_name:
                    inv_line_name = inv_line_name.replace(marker, value)

            inv_line_data = {
                "price_unit": amount,
                "quantity": 1.0,
                "fees_definition_id": fees_def.id,
                "name": inv_line_name,
            }

            if inv is None:
                inv = fees_def.model_invoice_id.copy({"date_invoice": self.until_date})
                inv.invoice_line_ids[0].update(inv_line_data)
            else:
                inv.invoice_line_ids[0].copy(inv_line_data)

        self.invoice_ids |= inv

    @api.multi
    def action_reset(self):
        "Reset a done computation into a draft and remove its details"
        self.ensure_one()

        if self.state != "done":
            raise UserError(
                _("Cannot reset fees computation if not in the 'done' state"),
            )
        if any(inv.state != "cancel" for inv in self.invoice_ids):
            raise UserError(
                _("Cannot reset fees computation with a non-canceled invoice"),
            )

        self.update({"state": "draft", "fees": 0.0, "invoice_ids": [(5,)]})
        self.sudo().detail_ids.unlink()

    @api.multi
    def action_run(self):
        "Run current computation(s)"
        for record in self:
            record.state = "running"
            record.with_delay()._run()

    def _add_compensation(
        self, fees_def, compensation_type, device, delivery_date, device_fees, to_date
    ):
        prices = fees_def.prices(device)

        compensation_price = max(
            device_fees,
            prices["standard"] - prices["purchase"],
        )

        self.env["rental_fees.computation.detail"].sudo().create(
            {
                "fees_computation_id": self.id,
                "fees": compensation_price,
                "fees_type": compensation_type,
                "lot_id": device.id,
                "from_date": delivery_date,
                "to_date": to_date,
                "fees_definition_id": fees_def.id,
            }
        )

    def _add_fees_periods(self, device, periods):
        for period in periods:
            def_line = period["fees_def_line"]
            self.env["rental_fees.computation.detail"].sudo().create(
                {
                    "fees_computation_id": self.id,
                    "fees": period["fees"],
                    "fees_type": "fees",
                    "lot_id": device.id,
                    "contract_id": period["contract"].id,
                    "from_date": period["from_date"],
                    "to_date": period["to_date"],
                    "fees_definition_id": def_line.fees_definition_id.id,
                    "fees_definition_line_id": def_line.id,
                }
            )

    @job(default_channel="root")
    def _run(self):
        self.ensure_one()
        for fees_def in self.fees_definition_ids:
            self._run_for_fees_def(fees_def)
        self.fees = sum(self.detail_ids.mapped("fees"))

        self.state = "done"
        for fees_def in self.fees_definition_ids:
            fees_def.last_non_draft_computation_date = max(
                self.until_date,
                fees_def.last_non_draft_computation_date or self.until_date,
            )

    def _run_for_fees_def(self, fees_def):

        scrapped_devices = fees_def.scrapped_devices(self.until_date)

        for device, delivery_date in fees_def.devices_delivery().items():

            periods = self.rental_periods(device)
            no_rental_limit, periods = self.scan_no_rental(
                fees_def, device, delivery_date, periods
            )

            if periods:
                periods = self.split_periods_wrt_fees_def(fees_def, periods)

            device_fees = 0.0
            for period in periods:
                period["fees"] = period["fees_def_line"].compute_fees(period)
                device_fees += period["fees"]

            if no_rental_limit:
                self._add_compensation(
                    fees_def,
                    "no_rental_compensation",
                    device,
                    delivery_date,
                    device_fees,
                    no_rental_limit,
                )
            elif device in scrapped_devices:
                self._add_compensation(
                    fees_def,
                    "lost_device_compensation",
                    device,
                    delivery_date,
                    device_fees,
                    scrapped_devices[device]["date"],
                )
            else:
                self._add_fees_periods(device, periods)


class RentalFeesComputationDetail(models.Model):
    _name = "rental_fees.computation.detail"
    _description = "Detailed results of a rental fees computation"
    _order = "lot_id ASC, from_date ASC"

    fees_computation_id = fields.Many2one(
        "rental_fees.computation",
        string="Computation",
        required=True,
    )

    fees = fields.Float(
        string="Computed fees",
        required=True,
    )

    fees_type = fields.Selection(
        [
            ("fees", "Rental Fees"),
            ("no_rental_compensation", "No rental compensation"),
            ("lost_device_compensation", "Lost device compensation"),
        ],
        string="Fees type",
        required=True,
    )

    lot_id = fields.Many2one(
        "stock.production.lot",
        string="Device",
        required=True,
    )

    contract_id = fields.Many2one(
        "contract.contract",
        string="Contract",
    )

    from_date = fields.Date(
        string="From date",
        required=True,
    )

    to_date = fields.Date(
        string="To date",
        required=True,
    )

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Fees definition",
    )

    fees_definition_line_id = fields.Many2one(
        "rental_fees.definition_line",
        string="Fees definition line",
    )

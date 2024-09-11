import logging
from functools import partial

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date

from odoo.addons.queue_job.job import job

_one_day = relativedelta(days=1)
_logger = logging.getLogger(__name__)


def _not_canceled(invoice):
    "Helper to filter opened and paid invoices"
    return invoice.state != "cancel"


def _filter_by_def(fees_def, detail):
    return detail.fees_definition_id == fees_def


def _with_fees(detail):
    return detail.fees_type == "fees" and detail.fees > 0.0


def _compensated(detail):
    return detail.fees_type != "fees"


class RentalFeesComputation(models.Model):
    _name = "rental_fees.computation"
    _description = "Computation of rental fees"
    _inherit = ["mail.thread"]
    _order = "partner_id,until_date desc"

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

    run_datetime = fields.Datetime(
        "Run datetime",
        default=False,
        copy=False,
        readonly=True,
        compute="_compute_run_datetime_and_has_forecast",
    )

    has_forecast = fields.Boolean(
        copy=False,
        readonly=True,
        compute="_compute_run_datetime_and_has_forecast",
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

    @api.depends("until_date", "state")
    def _compute_run_datetime_and_has_forecast(self):
        now = fields.Datetime.now()
        for record in self:
            if record.state == "running":
                record.run_datetime = now
                record.has_forecast = record.until_date > record.run_datetime.date()
            else:
                record.run_datetime = False
                record.has_forecast = record.until_date > now.date()

    def details(self, *fees_types):
        return self.detail_ids.filtered(lambda d: d.fees_type in fees_types)

    def rental_details(self):
        return self.details("fees")

    def compensation_details(self):
        field = self.env["rental_fees.computation.detail"].fields_get()["fees_type"]
        compensation_fees_types = [
            _type[0] for _type in field["selection"] if "compensation" in _type[0]
        ]
        return self.details(*compensation_fees_types)

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
            device: (fees_def, delivery_data["order_line"])
            for fees_def in self.fees_definition_ids
            for device, delivery_data in fees_def.devices_delivery().items()
        }

        result = {}

        for device in sorted(purchase_data, key=lambda d: d.product_id):
            fees_def, ol = purchase_data[device]
            prices = fees_def.prices(device)

            fees = fees_data.get(device.id, 0.0)
            result[device] = {
                "purchase": ol.order_id,
                "purchase_line": ol,
                "purchase_price": prices["purchase"],
                "without_agreement": prices["standard"],
                "fees": fees,
                "total": prices["purchase"] + fees,
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

        if self.has_forecast:
            last_real_date = self.run_datetime.date()
        else:
            last_real_date = self.until_date

        move_lines = (
            self.env["stock.move.line"]
            .search(
                [
                    ("state", "=", "done"),
                    ("lot_id", "=", device.id),
                    ("move_id.date", "<", last_real_date + _one_day),
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
                        "Device %s was already at customer location" % device.name
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
            current_period["to_date"] = last_real_date + _one_day
            result.append(current_period)

            if self.has_forecast:
                result.append(
                    dict(
                        current_period,
                        from_date=current_period["to_date"],
                        to_date=self.until_date + _one_day,
                        is_forecast=True,
                    )
                )

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

    def split_periods_wrt_fees_def(self, fees_def, periods):
        """Split given periods into smaller ones wrt. given fees def

        ... and add the corresponding line definition to the resulting
        periods. Each given fees definition line defines a period on
        which the amount of the fees is uniform.
        """
        if not fees_def.line_ids:
            msg = _("Fees definition %s (id %d) has no line.")
            raise UserError(msg % (fees_def.name, fees_def.id))

        result = []
        line_iter = iter(fees_def.line_ids)
        fees_def_line = next(line_iter)

        split_date = fees_def_line.compute_end_date(periods[0]["from_date"])

        for p_num, period in enumerate(periods):
            while True:

                from_date = (
                    max(result[-1]["to_date"], period["from_date"])
                    if result
                    else period["from_date"]
                )

                if split_date and split_date < period["to_date"]:
                    result.append(
                        {
                            "contract": period["contract"],
                            "is_forecast": period["is_forecast"],
                            "from_date": from_date,
                            "to_date": split_date,
                            "fees_def_line": fees_def_line,
                        }
                    )

                    fees_def_line = next(line_iter)
                    split_date = fees_def_line.compute_end_date(split_date)

                else:
                    result.append(
                        {
                            "contract": period["contract"],
                            "is_forecast": period["is_forecast"],
                            "from_date": from_date,
                            "to_date": period["to_date"],
                            "fees_def_line": fees_def_line,
                        }
                    )

                    if split_date and p_num < len(periods) - 1:
                        gap = periods[p_num + 1]["from_date"] - period["to_date"]
                        split_date += gap

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

    def devices_summary(self):
        """Return the total and by fees def device number summary of present computation

        Return value is of the form:
        {
            "by_fees_def": {
                <fees_def>: {
                    "rental_fees": <rental fees amount>,
                    "compensations": <compensation fees amount>,
                    "fees": <sum of both types above>,
                    "invoiced": <already invoiced fees for this definition>,
                    "to_invoice": <fees - invoiced>,
                },
            },
            "totals": {
                "rental_fees": <total rental fees amount>,
                "compensations": <total compensation fees amount>,
                "fees": <sum of both types above>,
                "invoiced": <total already invoiced fees>,
                "to_invoice": <fees - invoiced>,
            },
        }
        """

        def nb_rented(fees_def):
            return self.env["rental_fees.computation.detail"].search_count(
                [
                    ("fees_computation_id", "=", self.id),
                    ("to_date", "=", self.until_date),
                    ("fees_definition_id", "=", fees_def.id),
                    ("fees_type", "=", "fees"),
                    ("fees", ">", 0.0),
                ]
            )

        result = {"by_fees_def": {}, "totals": {}}
        for fees_def in self.fees_definition_ids:
            details = self.detail_ids.filtered(partial(_filter_by_def, fees_def))
            with_fees = details.filtered(_with_fees)
            compensated = details.filtered(_compensated)

            result["by_fees_def"][fees_def] = {
                "bought": len(fees_def.devices_delivery()),
                "rented": nb_rented(fees_def),
                "with_fees": len(with_fees.mapped("lot_id")),
                "compensated": len(compensated.mapped("lot_id")),
            }

        # Add totals
        keys = list(result["by_fees_def"][fees_def].keys())
        result["totals"] = {
            key: sum(values[key] for values in result["by_fees_def"].values())
            for key in keys
        }

        return result

    def amounts_summary(self):
        """Return the total and by fees def amounts summary of present computation

        Return value is of the form:
        {
            "by_fees_def": {
                <fees_def>: {
                    "rental_fees": <rental fees amount>,
                    "compensations": <compensation fees amount>,
                    "fees": <sum of both types above>,
                    "invoiced": <already invoiced fees for this definition>,
                    "to_invoice": <fees - invoiced>,
                },
            },
            "totals": {
                "rental_fees": <total rental fees amount>,
                "compensations": <total compensation fees amount>,
                "fees": <sum of both types above>,
                "invoiced": <total already invoiced fees>,
                "to_invoice": <fees - invoiced>,
            },
        }
        """

        def fees_type(detail):
            return "rental_fees" if detail.fees_type == "fees" else "compensations"

        self_invl = self.invoice_ids.filtered(_not_canceled).mapped("invoice_line_ids")

        result = {"by_fees_def": {}, "totals": {}}
        for fees_def in self.fees_definition_ids:
            details = self.detail_ids.filtered(partial(_filter_by_def, fees_def))

            fees_by_type = {"rental_fees": 0.0, "compensations": 0.0}
            for detail in details:
                fees_by_type[fees_type(detail)] += detail.fees

            fees = sum(fees_by_type.values())
            fees_def_invl = fees_def.invoice_line_ids.filtered(
                lambda invl: invl.invoice_id.state != "cancel"
                and invl.invoice_id.date_invoice < self.until_date
            )
            invoiced = sum((fees_def_invl - self_invl).mapped("price_subtotal"))
            result["by_fees_def"][fees_def] = dict(
                fees_by_type, fees=fees, invoiced=invoiced, to_invoice=fees - invoiced
            )

        # Add totals
        keys = list(result["by_fees_def"][fees_def].keys())
        result["totals"] = {
            key: sum(values[key] for values in result["by_fees_def"].values())
            for key in keys
        }

        return result

    @api.multi
    def button_open_details(self):
        self.ensure_one()
        return {
            "name": _("Fees computation details"),
            "domain": [("fees_computation_id", "=", self.id)],
            "type": "ir.actions.act_window",
            "view_mode": "tree,graph,pivot,form",
            "res_model": "rental_fees.computation.detail",
        }

    @api.multi
    def button_open_job(self):
        self.ensure_one()
        domain = [("func_string", "=", "rental_fees.computation(%s,)._run()" % self.id)]
        job = self.env["queue.job"].search(domain, limit=1)
        if job:
            return {
                "name": _("Fees computation job"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "queue.job",
                "res_id": job.id,
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

        amounts_by_def = self.amounts_summary()["by_fees_def"]
        invoice_model = next(iter(amounts_by_def)).model_invoice_id
        if not invoice_model:
            raise UserError(_("Please set the invoice model on all fees definitions."))

        for fees_def, amounts in amounts_by_def.items():

            if self._has_later_invoiced_computation():
                raise UserError(
                    _("There is a later invoice for the same fees definition")
                )

            if fees_def.model_invoice_id != invoice_model:
                raise UserError(
                    _("Please use the same invoice model on all fees definition."),
                )

            inv_line_name = fees_def.model_invoice_id.invoice_line_ids[0].name
            markers = {"##DATE##": until_date, "##FEES_DEF##": fees_def.name}
            for marker, value in markers.items():
                if marker in inv_line_name:
                    inv_line_name = inv_line_name.replace(marker, value)

            inv_line_data = {
                "price_unit": amounts["to_invoice"],
                "quantity": 1.0,
                "fees_definition_id": fees_def.id,
                "name": inv_line_name,
            }

            if inv is None:
                inv = fees_def.model_invoice_id.copy({"date_invoice": self.until_date})
                inv.invoice_line_ids[0].update(inv_line_data)
            else:
                inv.invoice_line_ids[0].copy(inv_line_data)

        inv._onchange_invoice_line_ids()
        self.invoice_ids |= inv

    @api.multi
    def action_send_report_for_invoicing(self):
        "Get or generate supplier invoice and report, send then it through the invoice"

        report_action = self.env.ref(
            "rental_fees.action_py3o_spreadsheet_fees_rental_computation"
        )

        def _draft_invoices():
            return self.invoice_ids.filtered(lambda invoice: invoice.state == "draft")

        def _create_invoice():
            self.action_invoice()
            return _draft_invoices()

        def _create_report():
            report_action.render(self.ids)
            return report_action.retrieve_attachment(self)

        # Get or create invoice and report
        inv = _draft_invoices() or _create_invoice()
        report = report_action.retrieve_attachment(self) or _create_report()

        # Send report from invoice
        mail = self.env.ref("rental_fees.send_report_mail_template")
        _inv = inv.with_context(default_attachment_ids=[(4, report.id)])
        _inv.message_post_with_template(mail.id)

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
        self,
        fees_def,
        compensation_type,
        device,
        delivery_date,
        device_fees=0.0,
        to_date=None,
        reason=None,
    ):
        prices = fees_def.prices(device)

        compensation_price = max(
            device_fees,
            prices["standard"] - prices["purchase"],
        )

        to_date = delivery_date if to_date is None else (to_date - _one_day)

        self.env["rental_fees.computation.detail"].sudo().create(
            {
                "fees_computation_id": self.id,
                "fees": compensation_price,
                "fees_type": compensation_type,
                "lot_id": device.id,
                "from_date": delivery_date,
                "to_date": to_date,
                "fees_definition_id": fees_def.id,
                "compensation_reason": reason,
            }
        )

    def _add_fees_periods(self, device, periods):
        "Insert computation details, further detailing the period in forecast mode"

        def insert_detail(fees, contract, from_date, to_date, def_line, is_forecast):
            self.env["rental_fees.computation.detail"].sudo().create(
                {
                    "fees_computation_id": self.id,
                    "fees": fees,
                    "fees_type": "fees",
                    "lot_id": device.id,
                    "contract_id": contract.id,
                    "from_date": from_date,
                    "to_date": to_date - _one_day,  # dates included in the DB
                    "fees_definition_id": def_line.fees_definition_id.id,
                    "fees_definition_line_id": def_line.id,
                    "is_forecast": is_forecast,
                }
            )

        for period in periods:
            if self.has_forecast:
                # Split by month to get a smooth fees vs. time graph:
                for from_date, to_date, amount in period["monthly_fees"]:
                    insert_detail(
                        amount,
                        period["contract"],
                        from_date,
                        to_date,
                        period["fees_def_line"],
                        period["is_forecast"],
                    )
            else:
                insert_detail(
                    period["fees"],
                    period["contract"],
                    period["from_date"],
                    period["to_date"],
                    period["fees_def_line"],
                    period["is_forecast"],
                )

    @job(default_channel="root")
    def _run(self):
        self.ensure_one()

        # Make the job idempotent:
        self.fees = 0.0
        self.sudo().detail_ids.unlink()

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
        excluded_devices = {ed.device: ed.reason for ed in fees_def.excluded_devices}

        for device, delivery_data in fees_def.devices_delivery().items():
            try:
                self._run_for_device(
                    fees_def,
                    device,
                    delivery_data,
                    scrapped_devices,
                    excluded_devices,
                )
            except:
                _logger.error(
                    "An error occurred while computing fees for device %s",
                    device.name,
                )
                raise

    def _run_for_device(
        self,
        fees_def,
        device,
        delivery_data,
        scrapped_devices,
        excluded_devices,
    ):
        delivery_date = delivery_data["date"]

        if device in excluded_devices:
            self._add_compensation(
                fees_def,
                "excluded_device_compensation",
                device,
                delivery_date,
                reason=excluded_devices[device],
            )
            return

        periods = self.rental_periods(device)
        no_rental_limit, periods = self.scan_no_rental(
            fees_def, device, delivery_date, periods
        )

        if periods:
            periods = self.split_periods_wrt_fees_def(fees_def, periods)

        device_fees = 0.0
        for period in periods:
            period["device"] = device.name  # helps debugging
            monthly_fees = period["fees_def_line"].compute_monthly_fees(period)
            period["monthly_fees"] = monthly_fees
            period["fees"] = sum(amount for _ds, _de, amount in monthly_fees)
            device_fees += period["fees"]

        if device in scrapped_devices:
            self._add_compensation(
                fees_def,
                "lost_device_compensation",
                device,
                delivery_date,
                device_fees,
                scrapped_devices[device]["date"],
            )
        elif no_rental_limit:
            self._add_compensation(
                fees_def,
                "no_rental_compensation",
                device,
                delivery_date,
                device_fees,
                no_rental_limit,
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
            ("excluded_device_compensation", "Excluded device compensation"),
        ],
        string="Fees type",
        required=True,
    )

    compensation_reason = fields.Char()

    lot_id = fields.Many2one(
        "stock.production.lot",
        string="Device",
        required=True,
    )

    product_template_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        readonly=True,
        related="lot_id.product_id.product_tmpl_id",
        store=True,
        index=True,
    )

    contract_id = fields.Many2one(
        "contract.contract",
        string="Contract",
    )

    contract_template_id = fields.Many2one(
        comodel_name="contract.template",
        string="Contract template",
        readonly=True,
        related="contract_id.contract_template_id",
        store=True,
        index=True,
    )

    market = fields.Selection(
        [("B2C", "B2C"), ("B2B", "B2B")],
        string="Market",
        readonly=True,
        compute="_compute_market",
        store=True,
        index=True,
    )

    from_date = fields.Date(
        string="From date",
        required=True,
    )

    to_date = fields.Date(
        string="To date",
        required=True,
    )

    is_forecast = fields.Boolean(
        "Is a forecast?",
        store=True,
        index=True,
    )

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Fees definition",
    )

    fees_definition_line_id = fields.Many2one(
        "rental_fees.definition_line",
        string="Fees definition line",
    )

    @api.depends("contract_template_id")
    def _compute_market(self):
        for record in self:
            ct_name = record.contract_template_id.name
            if ct_name and "/" in ct_name:
                market = ct_name.split("/", 2)[1]
                record.market = "B2C" if market == "B2C" else "B2B"
            else:
                record.market = False

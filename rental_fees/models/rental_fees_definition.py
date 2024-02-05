import json

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import misc


def month_intervals(period):
    one_month = relativedelta(months=1)
    from_date = period["from_date"]
    while from_date < period["to_date"]:
        to_date = from_date + one_month
        yield from_date, to_date
        from_date = to_date


class RentalFeesDefinition(models.Model):
    _name = "rental_fees.definition"
    _description = (
        "A definition of fees to be paid back to the supplier when renting his hardware"
    )

    name = fields.Char(required=True, copy=False)

    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        help="The supplier concerned by this fees definition",
        required=True,
        domain=[("supplier", "=", True)],
    )

    model_invoice_id = fields.Many2one(
        "account.invoice",
        string="Invoice model",
        help=(
            "Invoice to be used as a model to generate future fees invoices."
            " First line MUST be the fees as their amount will be replaced by"
            " the computed amount."
            " The optional marker ##DATE## in an invoice line description will"
            " be replaced by the fees computation date."
        ),
        domain='[("partner_id", "=", partner_id), ("type", "=", "in_invoice")]',
    )

    product_template_id = fields.Many2one(
        "product.template",
        string="Product",
        help="The product concerned by this fees definition",
        required=True,
        domain=[("type", "=", "product")],
    )

    agreed_to_std_price_ratio = fields.Float(
        "Agreed / standard price ratio",
        required=True,
        help=(
            "Ratio between the purchase price in this fees agreement"
            " and the standard price. Used for compensation in case of a"
            " device breakage."
        ),
    )

    penalty_period_duration = fields.Integer(
        "No rental penalty period duration (in years)",
        required=True,
        default=0,
        help=(
            "During this number of years after the device delivery,"
            " penalty fees will be paid for devices that have not been"
            " rented for a too long time."
        ),
    )

    no_rental_duration = fields.Integer(
        "No rental duration before penalty (months)",
        required=True,
        default=0,
        help=(
            "During a certain period after the device delivery, penalty fees"
            " will be paid for a device that would not have been rented for"
            " this number of consecutive months."
        ),
    )

    excluded_devices = fields.One2many(
        comodel_name="rental_fees.excluded_device",
        string="Explicitely excluded devices (with compensation)",
        inverse_name="fees_definition_id",
        copy=False,
    )

    invoice_line_ids = fields.One2many(
        comodel_name="account.invoice.line",
        string="Invoice lines",
        inverse_name="fees_definition_id",
        help=("The invoice lines related to present fees definition."),
        copy=False,
    )

    order_ids = fields.Many2many(
        comodel_name="purchase.order",
        string="Purchase orders",
        domain=(
            "["
            " ('partner_id', '=', partner_id),"
            " ('order_line.product_id.product_tmpl_id', '=', product_template_id)"
            "]"
        ),
    )

    line_ids = fields.One2many(
        comodel_name="rental_fees.definition_line",
        string="Fees definition lines",
        inverse_name="fees_definition_id",
        copy=False,
    )

    # Computed on computation's state change
    last_non_draft_computation_date = fields.Date(default=False)

    @api.multi
    def write(self, vals):
        "Deny changing an important field (like partner_id or product_template_id)"

        important_fields_updated = bool(
            set(vals) & {"partner_id", "product_template_id"}
        )
        for record in self:
            if record.last_non_draft_computation_date and important_fields_updated:
                raise ValidationError(
                    _(
                        "Some non-draft computations use this fees definition."
                        " Please remove or set them draft to modify the definition."
                    )
                )

        return super().write(vals)

    @api.constrains("partner_id")
    def _check_partner_coherency(self):
        for fees_def in self:
            if fees_def.mapped("order_ids.partner_id") != self.partner_id:
                raise models.ValidationError(
                    _(
                        "Fees definition purchase orders partners must all be"
                        " the same as the fees definition's partner"
                    )
                )

    @api.constrains("partner_id", "product_template_id", "order_ids")
    def _check_no_po_override(self):
        for fees_def in self:
            overrides = self.env[self._name].search(
                [
                    ("id", "!=", fees_def.id),
                    ("partner_id", "=", fees_def.partner_id.id),
                    ("product_template_id", "=", fees_def.product_template_id.id),
                    ("order_ids", "in", fees_def.order_ids.ids),
                ]
            )
            if overrides:
                raise models.ValidationError(
                    _(
                        "At least one other fees def, %s (id %d), has the same"
                        " partner, product & order"
                    )
                    % (overrides[0].name, overrides[0].id)
                )

    def devices_delivery(self):
        result = {}
        for ol in self.mapped("order_ids.order_line").filtered(
            lambda ol: ol.product_id.product_tmpl_id == self.product_template_id
        ):
            for ml in ol.mapped("move_ids.move_line_ids"):
                for device in ml.mapped("lot_id"):
                    result[device] = {"order_line": ol, "date": ml.date.date()}
        return result

    def scrapped_devices(self, date):
        quants = self.env["stock.quant"].search(
            [
                ("lot_id", "in", [d.id for d in self.devices_delivery()]),
                ("quantity", ">", 0.0),
                ("location_id.scrap_location", "=", True),
                ("in_date", "<=", date),
            ]
        )

        return {
            quant.lot_id: {
                "date": quant.in_date.date(),
            }
            for quant in quants
        }

    def prices(self, device):
        "Return device invoiced mean price"
        po_line = self.env["purchase.order.line"].search(
            [
                ("order_id", "in", self.order_ids.ids),
                ("move_ids.move_line_ids.lot_id", "=", device.id),
            ]
        )
        # PO line price is indicative, use the invoice lines mean price
        inv_lines = po_line.invoice_lines.filtered(
            lambda il: il.invoice_id.state != "cancel"
        )
        if not inv_lines:
            msg = _(
                "No price for device %(serial)s: its PO line has no invoice, see %(po)s"
            )
            raise UserError(msg % {"serial": device.name, "po": po_line.order_id.name})

        mean_price_unit = sum(il.price_unit * il.quantity for il in inv_lines) / sum(
            inv_lines.mapped("quantity")
        )
        return {
            "purchase": mean_price_unit,
            "standard": mean_price_unit / self.agreed_to_std_price_ratio,
        }

    @api.multi
    def button_open_devices(self):
        self.ensure_one()
        return {
            "name": _("Devices"),
            "domain": [("id", "in", [d.id for d in self.devices_delivery()])],
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "stock.production.lot",
        }


class RentalFeesDefinitionLine(models.Model):
    _name = "rental_fees.definition_line"
    _description = "Define how to compute rental fees value on a period of time"
    _order = "sequence, id"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Fees definition",
        required=True,
        ondelete="cascade",
    )

    sequence = fields.Integer(
        string="Index of the period in the fees definition",
        help="Useful to order the periods in the fees definition",
        required=True,
    )

    duration_value = fields.Integer(
        string="Duration value",
        help=(
            "Value of the duration of the period, in duration units."
            " No duration_value means infinite duration."
        ),
    )

    duration_unit = fields.Selection(
        [
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
            ("years", "Years"),
        ],
        string="Duration unit",
        help="Units of the duration of the period",
        default="months",
        required=True,
    )

    fees_type = fields.Selection(
        [("fix", "Fixed"), ("proportional", "Proportional")],
        string="Fees type",
        help=(
            "Fixed: value is a monthly time-independent amount. "
            "Proportional: value is the monthly fees for full price"
            " - fees will be computed proportionally with today's price"
        ),
        default="fix",
        required=True,
    )

    monthly_fees = fields.Float(
        string="Monthly fees",
        help="This value is to be interpreted using fees type",
        required=True,
    )

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, str(record.sequence)))
        return result

    @api.multi
    def compute_end_date(self, origin_date):
        self.ensure_one()
        if self.duration_value:
            return origin_date + relativedelta(
                **{self.duration_unit: self.duration_value}
            )

    @api.multi
    def compute_monthly_fees(self, period):
        """Return a (from_date, to_date, amount) list of monthly fees for the period

        When contract periodicity is bigger than a month, the fees may
        be 0 for a while then paid in one big go.

        When the period is a forecast, we use the contract forecast table,
        otherwise the invoice table is used.
        """

        self.ensure_one()

        result = []

        if self.fees_type == "fix":
            for from_date, to_date in month_intervals(period):
                result.append((from_date, to_date, self.monthly_fees))

        elif self.fees_type == "proportional":
            if period["is_forecast"]:
                forecasts = self.env["contract.line.forecast.period"].search(
                    [
                        ("contract_id", "=", period["contract"].id),
                        ("date_invoice", ">=", period["from_date"]),
                        ("date_invoice", "<", period["to_date"]),
                    ]
                )
                date_amounts = [(p.date_invoice, p.price_subtotal) for p in forecasts]
            else:
                date_amounts = self._get_invoiced_amounts(period)

            for from_date, to_date in month_intervals(period):
                total = 0.0
                for date, amount in date_amounts:
                    if from_date <= date < to_date:
                        total += amount
                result.append((from_date, to_date, total * self.monthly_fees))

        return result

    def _get_invoiced_amounts(self, period):
        """Return a (date, amount) list of invoiced amounts for the given fees period

        This includes invoices directly generated from the contract but also the
        invoices that have been merged (and thus cancelled). The latter are identified
        using the merged invoice line analytic account, that must match the period's
        contract lines one.
        """

        try:
            cline = period["contract"].get_main_rental_line()
        except ValidationError as err:
            msg = _(
                "\n%(err)s\n"
                "Previous error occurred while computing the invoiced amounts of this"
                " period in fees definition %(def_name)r (id %(def_id)d):\n- %(period)s"
            )
            raise RuntimeError(
                msg
                % {
                    "err": err.name,
                    "def_name": self.fees_definition_id.name,
                    "def_id": self.fees_definition_id.id,
                    "period": "\n- ".join("%s: %s" % (k, v) for k, v in period.items()),
                }
            )
        paid_invoice_lines = self.env["account.invoice.line"].search(
            [
                ("contract_line_id", "=", cline.id),
                ("date_invoice", ">=", period["from_date"]),
                ("date_invoice", "<", period["to_date"]),
                ("state", "=", "paid"),
            ]
        )

        analytic_accounts = period["contract"].mapped(
            "contract_line_ids.analytic_account_id"
        )
        merged_invoice_lines = self.env["account.invoice.line"].search(
            [
                ("invoice_type", "=", "out_invoice"),
                ("date_invoice", ">=", period["from_date"]),
                ("date_invoice", "<", period["to_date"]),
                ("state", "=", "paid"),
                ("contract_line_id", "=", False),
                ("account_analytic_id", "in", analytic_accounts.ids),
            ]
        )

        return [
            (il.date_invoice, il.price_subtotal)
            for il in (paid_invoice_lines + merged_invoice_lines)
        ]

    def format_fees_amount(self):
        if self.fees_type == "proportional":
            return "%.02f %%" % (100 * self.monthly_fees)

        elif self.fees_type == "fix":
            return _("%(fixed_amount)s %(currency)s (fixed)") % {
                "fixed_amount": misc.formatLang(
                    self.env,
                    self.monthly_fees,
                    monetary=True,
                ),
                "currency": self.env.user.company_id.currency_id.symbol,
            }


class RentalFeesExcludedDevice(models.Model):
    _name = "rental_fees.excluded_device"
    _description = "Represents a device excluded from the fees and the reason for it"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Rental fees definition",
        required=True,
    )

    device = fields.Many2one(
        "stock.production.lot",
        string="Device",
        help="The device to be excluded",
        required=True,
    )

    device_domain = fields.Char(
        default=lambda self: self._default_device_domain(),
        readonly=True,
        store=False,
    )

    reason = fields.Char()

    def _default_device_domain(self):
        key = "default_fees_definition_id"
        if key in self.env.context:
            _def = self.env["rental_fees.definition"].browse(self.env.context[key])
            return json.dumps([("id", "in", [d.id for d in _def.devices_delivery()])])

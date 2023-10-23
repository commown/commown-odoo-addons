import datetime

from dateutil import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from .common import _force_picking_date


class StockPicking(models.Model):
    _inherit = "stock.picking"

    contract_ids = fields.Many2many(
        "contract.contract",
        string="Contract",
        compute="_compute_contract_ids",
        store=False,
    )

    @api.depends("move_lines.contract_id")
    def _compute_contract_ids(self):
        """Cannot be done with a related because odoo cannot deal with it

        See https://github.com/odoo/odoo/blob/12.0/odoo/fields.py#L571
        """
        for record in self:
            record.contract_ids = self.move_lines.mapped("contract_id")

    @api.multi
    def action_set_date_done_to_scheduled(self):
        for rec in self:
            if not rec.state == "done":
                raise UserError(_("Transfer must be done to use this action"))

            _force_picking_date(rec, rec.scheduled_date)

    @api.model
    def _cron_count_late_lot_pickings(self):
        fil = self.env.ref("commown_devices.late_pickings_with_lots_filter")
        filter_domain = safe_eval(
            fil.domain,
            {"datetime": datetime, "relativedelta": relativedelta.relativedelta},
        )
        late_pickings = self.env["stock.picking"].search_count(filter_domain)
        if late_pickings > 0:
            channel = self.env.ref("commown_devices.late_pickings_with_lots_channel")
            template = self.env.ref("commown_devices.late_pickings_with_lots_mail")
            channel.with_context(
                {"late_pickings": late_pickings}
            ).message_post_with_template(template.id)

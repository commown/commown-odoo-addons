from datetime import date, timedelta

from odoo import fields, models

DEFAULT_DELTA_WEEKS_CONTRACT_START = (
    6  # In case the delta_contract_start ir config parameter was deleted
)


class Contract(models.Model):
    _inherit = "contract.contract"

    def write(self, vals):
        if "date_start" in vals:
            date_start = vals["date_start"]
            if isinstance(date_start, str):
                date_start = fields.Date.from_string(date_start)

            param_delta_length = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "commown_b2b_mail_channel.delta_weeks_contract_start",
                    DEFAULT_DELTA_WEEKS_CONTRACT_START,
                )
            )
            # Timedelta is here to cover cases where the contract is manually started
            # with a date in te future
            if date_start < date.today() + timedelta(weeks=param_delta_length):
                self.partner_id.commercial_partner_id.sudo().create_mail_channel()

        return super().write(vals)

    def is_active_contract(self):
        if self.date_start and self.date_start <= date.today():
            return not self.date_end or self.date_end > date.today()
        else:
            return False

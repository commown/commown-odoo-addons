from datetime import date, timedelta

from odoo import api, models

DELTA_CONTRACT_START = timedelta(weeks=26)


class Contract(models.Model):
    _inherit = "contract.contract"

    def is_active_contract(self):
        if self.date_start and self.date_start <= date.today():
            return not self.date_end or self.date_end > date.today()
        else:
            return False

    @api.constrains("date_start")
    def on_contract_start_create_channel(self):
        """Trigger support channel creation if contract is about to start"""
        if self.date_start and self.date_start < date.today() + DELTA_CONTRACT_START:
            self.partner_id.commercial_partner_id.sudo().create_mail_channel()

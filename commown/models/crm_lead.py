from datetime import date

from odoo import api, fields, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    contract_id = fields.Many2one(
        domain="[('commercial_partner_id', '=', commercial_partner_id)]",
    )

    @api.multi
    def delivery_perform_actions(self):
        super().delivery_perform_actions()
        today = date.today()
        for record in self:
            # Current method may be called by users not allowed to update
            # contracts, so we use sudo here:
            contract = record.contract_id.sudo()
            # Do not restart contract that have already started
            if contract.date_start and contract.date_start <= today:
                continue
            contract.date_start = record.delivery_date

from odoo import api, fields, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    contract_id = fields.Many2one(
        domain="[('commercial_partner_id', '=', commercial_partner_id)]",
    )

    @api.model
    def create(self, vals):
        result = super().create(vals)
        if not result.contract_id:
            result.send_email_on_delivery = False
        return result

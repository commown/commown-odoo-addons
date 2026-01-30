from odoo import api, fields, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    contract_id = fields.Many2one(
        domain="[('commercial_partner_id', '=', commercial_partner_id)]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        if not self._context.get("test_commown_shipping_no_contract_check", False):
            result.filtered(lambda lead: not lead.contract_id).write(
                {"send_email_on_delivery": False}
            )
        return result

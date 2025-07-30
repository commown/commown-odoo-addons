from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        partner_ids = {vals["partner_id"] for vals in vals_list if "partner_id" in vals}
        for partner_id in partner_ids:
            partner = self.env["res.partner"].browse(partner_id)
            partner._update_subscription_on_user_creation()
        return res

    def unlink(self):
        part = self.partner_id
        res = super().unlink()
        if part:
            part._update_subscription_on_user_creation()
        return res

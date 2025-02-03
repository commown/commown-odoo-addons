from odoo import api, models


class ResUsers(models.Model):

    _inherit = "res.users"

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        res = super().create(vals)
        if "partner_id" in vals:
            self.env["res.partner"].browse(
                vals["partner_id"]
            )._update_subscription_on_user_creation()
        return res

    @api.multi
    def unlink(self):
        part = self.partner_id
        res = super().unlink()
        if part:
            part._update_subscription_on_user_creation()
        return res

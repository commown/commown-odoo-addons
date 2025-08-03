from odoo import fields, models


class CommownPartner(models.Model):
    _inherit = "res.partner"

    def _default_country(self):
        return self.env["res.company"]._company_default_get().country_id

    country_id = fields.Many2one(default=_default_country)

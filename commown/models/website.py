from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    product_service_details_url = fields.Char("Service detail URL", translate=True)

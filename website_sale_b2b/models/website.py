from odoo import models


class B2BWebsite(models.Model):
    _inherit = "website"

    def _display_partner_b2b_fields(self):
        """
        To avoid displaying the Odoo website_sale.address B2B fields,
        behaving differently from what we intend and displayed based on this method,
        we override it to always return False.
        """
        return False

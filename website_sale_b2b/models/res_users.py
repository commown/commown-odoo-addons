from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def is_authorized_to_order(self):
        """Return True if present user is authorized to place an order:

        - either has no company (yet): B2C or first employee/ individual business
        - or is in the group_customer_purchase group
        """
        if self.partner_id.commercial_partner_id.is_company:
            _group_ref = "customer_manager_base.group_customer_purchase"
            return self in self.env.ref(_group_ref).users

        return True

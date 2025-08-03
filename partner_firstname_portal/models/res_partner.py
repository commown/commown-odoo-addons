from odoo import api, models


class CommownPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def signup_retrieve_info(self, token):
        """Override auth_signup method for compat with partner_firstname:
        retrieve first- and last- name for the reset password form.
        """
        res = super().signup_retrieve_info(token)
        partner = self._signup_retrieve_partner(token, raise_exception=True)
        if partner.signup_valid:
            res["firstname"] = partner.firstname
            res["lastname"] = partner.lastname
        return res

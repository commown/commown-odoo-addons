from odoo import _, models


class WizardPartnerMoveLine(models.Model):
    _inherit = "account.move.line"

    def name_get(self):
        res = super().name_get()
        if not self.env.context.get("in_force_aml_partner_wizard"):
            return res

        dict_res = dict(res)
        for line in self:
            dict_res[line.id] = (
                _("(Account #%s) ", line.account_id.code) + dict_res[line.id]
            )
        return list(dict_res.items())

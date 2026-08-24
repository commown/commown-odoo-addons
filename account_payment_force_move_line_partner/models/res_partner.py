from odoo import models


class WizardResPartner(models.Model):
    _inherit = "res.partner"

    def name_get(self):
        "In the force partner wizard, display the partner type in the display name"
        res = super().name_get()
        if not self.env.context.get("in_force_aml_partner_wizard"):
            return res

        dict_res = dict(res)
        field = self.fields_get("type", "selection")
        partner_types = dict(field["type"]["selection"])

        for partner in self:
            type_name = partner_types[partner.type]
            dict_res[partner.id] = "(%s) %s" % (type_name, dict_res[partner.id])

        return list(dict_res.items())

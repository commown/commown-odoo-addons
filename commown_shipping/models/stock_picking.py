from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    carrier_required = fields.Boolean(default=False)

    def _laposte_fr_get_service(self, account, package=None):
        vals = self._roulier_get_service(account, package=package)

        if vals.get("product") != "COLI":
            vals.pop("returnTypeChoice", None)
        else:
            vals["returnTypeChoice"] = 3  # do not return to sender

        if getattr(origin := self.origin_entity(), "get_label_ref", None):
            vals["reference1"] = origin.get_label_ref()

        return vals

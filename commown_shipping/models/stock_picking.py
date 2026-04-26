from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _laposte_fr_get_service(self, account, package=None):
        vals = self._roulier_get_service(account, package=package)

        if getattr(origin := self.origin_entity(), "get_label_ref", None):
            vals["reference1"] = origin.get_label_ref()

        return vals

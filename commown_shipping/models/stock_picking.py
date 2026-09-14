from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    carrier_required = fields.Boolean(default=False)
    carrier_domain = fields.Char()

    def _laposte_fr_get_service(self, account, package=None):
        vals = self._roulier_get_service(account, package=package)

        if vals.get("product") != "COLI":
            vals.pop("returnTypeChoice", None)
        else:
            vals["returnTypeChoice"] = 3  # do not return to sender

        if getattr(origin := self.origin_document(), "get_label_ref", None):
            vals["reference1"] = origin.get_label_ref()

        return vals

    def action_generate_label(self):
        if self.carrier_tracking_ref:  # pragma: no cover
            return  # UI makes this impossible, this is defensive code

        result = self._roulier_generate_labels()
        if result:
            for label in result[0].get("labels", []):
                self.attach_shipping_label(label)
                if label.get("tracking_number") and not self.carrier_tracking_ref:
                    self.carrier_tracking_ref = label["tracking_number"]

from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    exclude_from_fees = fields.Boolean(
        string="Exclude from fees",
        help="Force exclusion from fees even if a matching fees definition exists",
        default=False,
    )

    @api.constrains("partner_id")
    def _check_partner_coherency(self):
        for po in self:
            fees_defs = self.env["rental_fees.definition"].search(
                [("order_ids", "in", self.ids)]
            )
            for fees_def in fees_defs:
                if fees_def.partner_id != po.partner_id:
                    raise models.ValidationError(
                        _(
                            "Purchase order's partner and its fees definition"
                            " must have the same partner"
                        )
                    )

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = [
        "crm.lead",
        "commown.track_delivery.mixin",
        "commown.shipping.mixin",
    ]

    # Used by recipient_partner_id domain
    commercial_partner_id = fields.Many2one(
        "res.partner", related="partner_id.commercial_partner_id"
    )

    _delivery_tracking_parent_rel = _shipping_parent_rel = "team_id"
    _delivery_tracking_stage_parent_rel = "team_id"

    so_line_id = fields.Many2one("sale.order.line", "Ligne de commande")
    delivery_tracking = fields.Boolean(
        "Delivery tracking", related="team_id.delivery_tracking"
    )

    @api.constrains("stage_id")
    def check_expedition_ref(self):
        if self.stage_id.name:
            if "[log: check exp-ref]" in self.stage_id.name and not self.expedition_ref:
                raise ValidationError(
                    _("Lead has no expedition ref. Please fill it in.")
                )

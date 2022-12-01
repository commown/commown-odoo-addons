import logging

from odoo import models

_logger = logging.getLogger(__file__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def create_b2b_opportunity(self):
        """Called when a big b2b customer submits an order request online

        An opportunity is created in the big_b2b_team commercial team.
        """

        self.ensure_one()
        _logger.info("Received big B2B order request for %s", self.name)

        team = self.env.ref("website_sale_b2b.big_b2b_team")
        stage = self.env.ref("website_sale_b2b.big_b2b_stage_new")
        company_name = self.partner_id.commercial_company_name or "?"
        lead = self.env["crm.lead"].create(
            {
                "name": "%s / %s" % (self.name, company_name),
                "partner_id": self.partner_id.id,
                "type": "opportunity",
                "team_id": team.id,
                "stage_id": stage.id,
                "so_line_id": self.order_line and self.order_line[0].id,
            }
        )
        # Override post-create behaviour that auto-assigns team and stage
        lead.update({"team_id": team.id, "stage_id": stage.id})
        return lead

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for record in self:
            record.create_risk_analysis_leads()
        return result

    def choose_stage(self, team):
        stages = self.env["crm.stage"].search(
            [("team_id", "=", team.id)], order="sequence"
        )
        stage = stages[0] if stages else self.env["crm.stage"]
        for _stage in stages:
            if "[stage: start]" in _stage.name:
                stage = _stage
                break
        return stage

    def related_contracts(self):
        return self.env["contract.contract"].of_sale(self)

    def _create_lead(self, name, team, so_line, **kwargs):
        data = {
            "name": name,
            "partner_id": self.partner_id.id,
            "type": "opportunity",
            "team_id": team.id,
            "stage_id": self.choose_stage(team).id,
            "so_line_id": so_line.id,
        }
        data.update(kwargs)
        lead = self.env["crm.lead"].create(data)
        # Override post-create behaviour that auto-assigns team_id
        lead.update({"team_id": team.id})
        return lead

    def risk_analysis_lead_title(self, so_line, contract=None, secondary_index=None):
        name = "%s-00" % self.name if contract is None else contract.name
        if secondary_index is not None:
            name += "/%s" % secondary_index
        return "[%s] %s" % (name, so_line.product_id.display_name)

    def create_risk_analysis_leads(self):
        """Create one risk analysis (RA) lead for each sold product with a followup team

        Set the contract if the product is managed by one.
        """

        self.ensure_one()

        leads = self.env["crm.lead"]

        clines = self.env["contract.line"].search(
            [
                ("sale_order_line_id.order_id", "=", self.id),
                ("sale_order_line_id.product_id.followup_sales_team_id", "!=", False),
            ]
        )

        managed_by_contract = {}
        for cline in clines:
            product = cline.sale_order_line_id.product_id
            for _num in range(int(cline.quantity)):
                managed_by_contract.setdefault(product, []).append(cline.contract_id)

        count = 0
        for so_line in self.order_line:
            product = so_line.product_id
            team = product.followup_sales_team_id
            if not team:
                continue
            for _num in range(int(so_line.product_uom_qty)):
                contracts = managed_by_contract.get(product, [])
                if contracts:
                    contract = contracts.pop()
                    lead = self._create_lead(
                        self.risk_analysis_lead_title(so_line, contract=contract),
                        team,
                        so_line,
                        contract_id=contract.id,
                    )
                else:
                    count += 1
                    name = self.risk_analysis_lead_title(so_line, secondary_index=count)
                    lead = self._create_lead(name, team, so_line)
                leads |= lead

        return leads

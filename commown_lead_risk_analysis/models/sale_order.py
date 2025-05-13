import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    _followup_by_usage = {
        "internal": {"parent": "followup_sales_team_id", "child": "crm.lead"},
        "customer": {"parent": "followup_sales_project_id", "child": "project.task"},
    }

    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for record in self:
            record._create_followup_entities()
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

    def _create_followup_entity_crm_lead(self, prefix, team, so_line, contract=None):
        lead = self.env["crm.lead"].create(
            {
                "name": " ".join([prefix, so_line.product_id.display_name]),
                "partner_id": self.partner_id.id,
                "type": "opportunity",
                "team_id": team.id,
                "stage_id": self.choose_stage(team).id,
                "so_line_id": so_line.id,
                "contract_id": contract.id if contract else False,
            }
        )
        # Override post-create behaviour that auto-assigns team_id
        lead.update({"team_id": team.id})
        return lead

    def _create_followup_entity_project_task(
        self, prefix, project, so_line, contract=None
    ):
        template = self.env.ref("commown_lead_risk_analysis.sale_task_description")
        description = template.render(
            {
                "prefix": prefix,
                "project": project,
                "so_line": so_line,
                "contract": contract,
            }
        )
        return self.env["project.task"].create(
            {
                "name": " ".join([prefix, so_line.product_id.name]),
                "partner_id": self.partner_id.id,
                "project_id": project.id,
                "stage_id": self.choose_stage(project).id,
                "contract_id": contract.id if contract else False,
                "description": description,
            }
        )

    def _followup_entity_title_prefix(self, contract=None, secondary_index=None):
        name = "%s-00" % self.name if contract is None else contract.name
        if secondary_index is not None:
            name += "/%s" % secondary_index
        return "[%s]" % name

    def _get_usage(self):
        contracts = self.mapped("order_line.product_id.property_contract_template_id")
        if contracts:
            usages = set(contracts.mapped("stock_ownership"))
            if len(usages) > 1:
                raise UserError(_("Cannot mix rental and sale with services contracts"))
            return next(iter(usages))
        else:
            product_types = self.mapped("order_line.product_id.type")
            if "product" in product_types:
                return "customer"
        return "internal"

    def _create_followup_entities(self):
        """Create one followup entity for each sold product with a followup team

        Set the contract if the product is managed by one.
        """

        self.ensure_one()

        usage = self._get_usage()
        parent_relation = self._followup_by_usage[usage]["parent"]
        entity_type = self._followup_by_usage[usage]["child"]
        create_entity_method = getattr(
            self, "_create_followup_entity_%s" % (entity_type.replace(".", "_"))
        )

        entities = self.env[entity_type]

        clines = self.env["contract.line"].search(
            [
                ("sale_order_line_id.order_id", "=", self.id),
                ("sale_order_line_id.product_id.%s" % parent_relation, "!=", False),
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
            parent = product[parent_relation]
            if not parent:
                continue

            contracts = managed_by_contract.get(product, [])
            for _num in range(int(so_line.product_uom_qty)):

                if contracts:
                    contract = contracts.pop()
                    prefix = self._followup_entity_title_prefix(contract=contract)
                    entity = create_entity_method(prefix, parent, so_line, contract)
                else:
                    count += 1
                    prefix = self._followup_entity_title_prefix(secondary_index=count)
                    entity = create_entity_method(prefix, parent, so_line)
                entities |= entity

        return entities

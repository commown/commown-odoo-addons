import html

from odoo import Command, _, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_investment_followup_task(self):
        product_tmpl_ids = (
            self.env["product.template"]
            .search([("is_equity", "=", True), ("equity_type", "=", "invest")])
            .ids
        )

        description = []
        for line in self.order_line:
            if line.product_id.product_tmpl_id.id in product_tmpl_ids:
                description.append(
                    _(
                        "<p><b>Sale number:</b> %(sale_name)s</p>"
                        "<p><b>Sale date:</b> %(year)d-%(month)d-%(day)d</p>"
                        "<p><b>Product:</b> %(product_name)s</p>",
                        sale_name=html.escape(self.name),
                        year=self.date_order.year,
                        month=self.date_order.month,
                        day=self.date_order.day,
                        product_name=html.escape(line.product_id.display_name),
                    )
                )

        if description:
            ref = self.env.ref
            project = ref("commown_investment_sale.investment_followup_project")
            stage = ref("commown_investment_sale.investment_followup_start_stage")
            self.env["project.task"].create(
                {
                    "project_id": project.id,
                    "name": line.order_partner_id.name,
                    "user_ids": [Command.set(project.user_id.ids)],
                    "partner_id": line.order_partner_id.id,
                    "stage_id": stage.id,
                    "description": "\n".join(description),
                }
            )

    def action_confirm(self):
        self._create_investment_followup_task()
        return super().action_confirm()

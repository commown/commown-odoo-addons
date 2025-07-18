import html

from odoo import _, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_investment_followup_task(self):
        product_tmpl_ids = (
            self.env["product.template"]
            .search([("is_equity", "=", True), ("equity_type", "=", "invest")])
            .ids
        )

        line_tmpl = _(
            "<p><b>Sale number:</b> {sale_name}</p>"
            "<p><b>Sale date:</b> {date.year}-{date.month}-{date.day}</p>"
            "<p><b>Product:</b> {product_name}</p>"
        )

        description = []
        for line in self.order_line:
            if line.product_id.product_tmpl_id.id in product_tmpl_ids:
                description.append(
                    line_tmpl.format(
                        sale_name=html.escape(self.name),
                        date=self.date_order,
                        product_name=html.escape(line.product_id.display_name),
                    )
                )

        if description:
            ref = self.env.ref
            project = ref("commown.investment_followup_project")
            self.env["project.task"].create(
                {
                    "project_id": project.id,
                    "name": line.order_partner_id.name,
                    "user_id": project.user_id.id,
                    "partner_id": line.order_partner_id.id,
                    "stage_id": ref("commown.investment_followup_start_stage").id,
                    "description": "\n".join(description),
                }
            )

    def action_confirm(self):
        self._create_investment_followup_task()
        return super().action_confirm()

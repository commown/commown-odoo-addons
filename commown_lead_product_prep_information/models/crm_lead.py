from odoo import fields, models


class CommownProductPrepLead(models.Model):
    _inherit = "crm.lead"

    product_info = fields.Html(
        "Product information",
        compute="_compute_product_info",
        sanitize_attributes=False,
    )

    def _compute_product_info(self):
        _render = self.env["ir.qweb"]._render
        for lead in self:
            if not lead.so_line_id:
                lead.product_info = False
            else:
                product_info = _render(
                    "commown_lead_product_prep_information.product_prep_summary",
                    {"lead": lead},
                )
                lead.product_info = product_info

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    followup_sales_team_id = fields.Many2one("crm.team", string="Followup sales team")

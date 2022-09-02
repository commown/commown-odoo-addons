from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_description_sale = fields.Text(
        "Sale description for the website",
        translate=True,
        help=(
            "A description of the Product that you want to communicate to "
            "your online customers."
        ),
    )

    @api.multi
    def is_b2b(self):
        self.ensure_one()
        return self.website_id == self.env.ref("website_sale_b2b.b2b_website")

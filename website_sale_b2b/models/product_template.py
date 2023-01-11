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

    description_sale_is_template = fields.Boolean(
        "Description for customers is a template",
        help=(
            "If set, the sale order line descriptions with this article are"
            " interpreted as mako templates, with 'record' being the order line,"
            " and recomputed as soon as the unit price of the order line changes."
        ),
        default=False,
    )

    @api.multi
    def is_b2b(self):
        self.ensure_one()
        return self.website_id == self.env.ref("website_sale_b2b.b2b_website")

from odoo import api, models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_description_sale = fields.Text(
        'Sale description for the website', translate=True,
        help=('A description of the Product that you want to communicate to '
              'your online customers.'))

    @api.multi
    def is_b2b(self):
        self.ensure_one()
        for category in self.public_categ_ids:
            if category.is_b2b():
                return True
        return False

import logging
from collections import defaultdict

from odoo import api, fields, models

_logger = logging.getLogger(__file__)


def _all_children(entities):
    children = entities.mapped("child_id")
    if not children:
        return entities
    return entities | _all_children(children)


class ResPartner(models.Model):
    _inherit = "res.partner"

    website_id = fields.Many2one(
        help="Website the user can log in. An empty value means all websites."
    )

    @api.multi
    def rented_quantity(self, product_template=None, product_category=None):
        """Return the number of devices rented by the partner (or its company)

        We MUST take not yet started contracts in consideration here
        (but not finished ones) as this method is used for volume
        price discount, and future contracts are welcome!

        We count rented devices which are a variant of the given
        product template or in the given web category. Note that one
        (and only one) of those two filters must be given, otherwise
        an AssertionError is raised.
        """

        self.ensure_one()
        assert (
            bool(product_template) != bool(product_category),
            "One of product_template and product_category must be given and non-empty",
        )

        today = fields.Date.today()

        clines = self.env["contract.line"].search(
            [
                "|",
                ("date_end", "=", False),
                ("date_end", ">", today),
                (
                    "contract_id.partner_id.commercial_partner_id",
                    "=",
                    self.commercial_partner_id.id,
                ),
            ]
        )

        rented_by_product = defaultdict(int)
        categories_by_product = {}
        for cline in clines:
            pt = cline.sale_order_line_id.product_id.product_tmpl_id
            if pt.property_contract_template_id:
                rented_by_product[pt.id] += cline.quantity
                categories_by_product[pt.id] = set(pt.public_categ_ids.ids)

        if product_template:
            assert product_template._name == "product.template"
            result = rented_by_product.get(product_template.id, 0.0)

        elif product_category:
            categ_ids = _all_children(product_category)
            result = sum(
                rented_by_product[p_id]
                for p_id, p_categ_ids in categories_by_product.items()
                if not p_categ_ids.isdisjoint(categ_ids.ids)
            )

        _logger.debug(
            "Rented quantity of partner %s with data %s is %d.",
            self.name,
            {
                "product": product_template,
                "product_category": product_category,
            },
            result,
        )

        return result

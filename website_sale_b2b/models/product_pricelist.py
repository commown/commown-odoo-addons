import logging

from odoo import api, fields, models

_logger = logging.getLogger(__file__)


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    account_for_rented_quantity = fields.Selection(
        [
            ("no", "No"),
            ("product-template", "At product level"),
            ("product-category", "At category level"),
        ],
        help=(
            "Take into account the quantity already rented by customer's"
            " company to compute which price rule to apply."
        ),
        default="no",
    )

    account_for_rented_quantity_category_ids = fields.Many2many(
        "product.public.category",
        "price_list_ids",
        help=(
            "List of the product web categories in which rental products"
            " will be counted for volume discounts."
        ),
    )

    def _search_suitable_category(self, product):
        assert self.account_for_rented_quantity == "product-category"
        suitable_ids = self.account_for_rented_quantity_category_ids.ids
        for categ in product.public_categ_ids:
            while categ:
                if categ.id in suitable_ids:
                    return categ
                categ = categ.parent_id
        else:
            _logger.warning(
                "Could not find a suitable category for product %s (id %d)"
                " in pricelist %s (id %d) among configured."
                "Pricelist categories are %s, product categories are %s.",
                product.name,
                product.id,
                self.name,
                self.id,
                self.account_for_rented_quantity_category_ids.ids,
                product.public_categ_ids.ids,
            )

    @api.multi
    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        self.ensure_one()
        choice = self.account_for_rented_quantity

        if choice not in ("no", False):

            _logger.debug(
                "Called _compute_price_rule with choice %s. Input data: %s",
                choice,
                products_qty_partner,
            )

            new_products_qty_partner = []
            suitable_category = {}

            for product, qty, partner in products_qty_partner:
                partner = (partner or self.env.user.partner_id).commercial_partner_id

                if choice == "product-template":
                    qty += partner.rented_quantity(product_template=product)

                elif choice == "product-category":

                    if product not in suitable_category:
                        suitable_category[product] = self._search_suitable_category(
                            product
                        )

                    categ = suitable_category[product]
                    _logger.debug(
                        "Pricelist category for product %s (%d): %s",
                        product.name,
                        product.id,
                        categ and categ.name or "None",
                    )

                    if categ is not None:
                        added_qty = partner.rented_quantity(product_category=categ)
                        qty += added_qty
                        _logger.debug("Rented quantity added: %s", added_qty)

                new_products_qty_partner.append((product, qty, partner))

            products_qty_partner = new_products_qty_partner
            _logger.debug(
                "  > calling base _compute_price_rule with data: %s",
                products_qty_partner,
            )

        return super(Pricelist, self)._compute_price_rule(
            products_qty_partner,
            date=date,
            uom_id=uom_id,
        )

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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
    def _rented_quantity_infos(self, product, partner):
        choice = self.account_for_rented_quantity
        infos = {"reason": None, "quantity": 0.0}

        if choice not in ("no", False):
            if choice == "product-template":
                infos["quantity"] = partner.rented_quantity(product_template=product)

            elif choice == "product-category":
                categ = self._search_suitable_category(product)
                _logger.debug(
                    "Pricelist category for product %s (%d): %s",
                    product.name,
                    product.id,
                    categ and categ.name or "None",
                )

                if categ is not None:
                    infos["quantity"] = partner.rented_quantity(product_category=categ)
                    infos["reason"] = categ

        return infos

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

            partner_model = self.env["res.partner"]

            for product, qty, partner in products_qty_partner:
                if isinstance(partner, int):
                    partner = partner_model.browse(partner) or self.env.user.partner_id
                partner = partner.commercial_partner_id
                rental_infos = self._rented_quantity_infos(product, partner)
                added_qty = rental_infos["quantity"]
                _logger.debug("Rented quantity infos: %s", rental_infos)
                new_products_qty_partner.append((product, qty + added_qty, partner))

            products_qty_partner = new_products_qty_partner
            _logger.debug(
                "  > calling base _compute_price_rule with data: %s",
                products_qty_partner,
            )

        result = super(Pricelist, self)._compute_price_rule(
            products_qty_partner,
            date=date,
            uom_id=uom_id,
        )

        _logger.debug("  > base _compute_price_rule result: %s", result)

        return result


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    percentage_exclude_extra = fields.Boolean(
        string="Exclude variant extra prices from reductions?",
        default=False,
    )

    def _compute_price(self, price, price_uom, product, quantity=1.0, partner=False):
        "Override to handle the percentage-extra-excluded case"

        if (
            product._name == "product.product"
            and self.compute_price == "percentage"
            and self.percentage_exclude_extra
        ):
            base_product = product.product_tmpl_id.product_variant_id
            wo_extra_price = base_product.price_compute(self.base)[base_product.id]
            reduced_wo_extra_price = super(PricelistItem, self)._compute_price(
                wo_extra_price,
                price_uom,
                product,
                quantity,
                partner,
            )
            extra_price = price - wo_extra_price
            result_price = reduced_wo_extra_price + extra_price
            _logger.debug(
                "Reduced price = reduced base (%.02f) + extra (%.02f) = %.02f",
                reduced_wo_extra_price,
                extra_price,
                result_price,
            )
            return result_price

        else:
            return super(PricelistItem, self)._compute_price(
                price,
                price_uom,
                product,
                quantity,
                partner,
            )

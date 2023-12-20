from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class RentedQuantityTC(RentalSaleOrderTC):
    def setUp(self):
        super(RentedQuantityTC, self).setUp()

        self.so = self.create_sale_order(self.env.ref("base.res_partner_address_1"))

        self.fp_premium = self._product_by_name("Fairphone Premium")
        self.fp2 = self._product_by_name("FP2")
        cat = self.env["product.public.category"]
        self.cat_fp = cat.create({"name": "FP"})
        self.cat_fp_premium = cat.create(
            {"name": "FP Premium", "parent_id": self.cat_fp.id}
        )
        self.fp2.public_categ_ids |= self.cat_fp
        self.fp_premium.public_categ_ids |= self.cat_fp_premium

        self.so.action_confirm()

        self.contracts = self.env["contract.contract"].of_sale(self.so)
        self.contracts.mapped("contract_line_ids").update({"date_start": "2022-01-01"})

    def _product_by_name(self, name):
        return self.env["product.template"].search([("name", "=", name)]).ensure_one()

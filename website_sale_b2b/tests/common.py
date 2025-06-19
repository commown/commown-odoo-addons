from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class RentedQuantityTC(RentalSaleOrderTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.so = cls.create_sale_order(cls.env.ref("base.res_partner_address_1"))

        cls.fp_premium = cls._product_by_name("Fairphone Premium")
        cls.fp2 = cls._product_by_name("FP2")
        cat = cls.env["product.public.category"]
        cls.cat_fp = cat.create({"name": "FP"})
        cls.cat_fp_premium = cat.create(
            {"name": "FP Premium", "parent_id": cls.cat_fp.id}
        )
        cls.fp2.public_categ_ids |= cls.cat_fp
        cls.fp_premium.public_categ_ids |= cls.cat_fp_premium

        cls.so.action_confirm()

        cls.contracts = cls.env["contract.contract"].of_sale(cls.so)
        cls.contracts.mapped("contract_line_ids").update({"date_start": "2022-01-01"})

    @classmethod
    def _product_by_name(cls, name):
        return cls.env["product.template"].search([("name", "=", name)]).ensure_one()

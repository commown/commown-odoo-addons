from odoo.exceptions import UserError

from .common import RentedQuantityTC


class ResPartnerTC(RentedQuantityTC):
    def test_rented_quantity(self):
        rented_quantity = self.so.partner_id.rented_quantity
        self.assertEqual(rented_quantity(product_template=self.fp_premium), 1)
        self.assertEqual(rented_quantity(product_template=self.fp2), 1)
        self.assertEqual(rented_quantity(product_category=self.cat_fp), 2)
        self.assertEqual(rented_quantity(product_category=self.cat_fp_premium), 1)

    def test_action_create_intermediate_company_error(self):
        comp = self.env["res.partner"].create({"name": "company", "is_company": True})
        c1 = self.env["res.partner"].create({"name": "c1"})
        c2 = self.env["res.partner"].create({"name": "c2", "parent_id": comp.id})
        c3 = self.env["res.partner"].create({"name": "c3"})

        with self.assertRaises(UserError) as err:
            (c1 | c2 | c3).action_create_intermediate_company()

        self.assertEqual(
            err.exception.name,
            "Partners not suitable for intermediate company creation:"
            "\n- c1 (id %d)\n- c3 (id %d)" % (c1.id, c3.id),
        )

    def test_action_create_intermediate_company_ok(self):
        comp = self.env["res.partner"].create({"name": "Company", "is_company": True})
        c1 = self.env["res.partner"].create({"name": "c1", "parent_id": comp.id})
        c2 = self.env["res.partner"].create({"name": "c2", "parent_id": comp.id})

        (c1 | c2).action_create_intermediate_company()

        self.assertEqual(c1.parent_id.parent_id, comp)
        self.assertEqual(c2.parent_id.parent_id, comp)
        self.assertTrue(c1.parent_id.is_company)
        self.assertTrue(c2.parent_id.is_company)
        self.assertEqual(c1.parent_id.name, "c1 (indep. - Company)")
        self.assertEqual(c2.parent_id.name, "c2 (indep. - Company)")

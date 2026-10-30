from lxml import html

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class LeadProductInformationTC(RentalSaleOrderTC):
    def test_lead_without_associated_product(self):
        lead = self.env["crm.lead"].create({"name": "Dummy lead"})
        self.assertFalse(lead.product_info)

        title = html.fromstring(lead.product_info_with_title).text
        self.assertEqual(title, lead.name)

    def test_lead_product_information_fields(self):
        tmpl_pc = self.env.ref("product_rental.prod_pc")
        cpu_i5 = self.env.ref("product_rental.val_cpu_i5")

        product = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", tmpl_pc.id),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    cpu_i5.id,
                ),
            ]
        )
        product.followup_sales_team_id = self.env.ref("sales_team.crm_team_1")

        so = self.env["sale.order"].create(
            {
                "partner_id": self.env.ref("base.user_demo").id,
                "order_line": [self._oline(product)],
            }
        )
        so.action_confirm()

        lead = self.env["crm.lead"].search([("so_line_id", "=", so.order_line.id)])
        self.assertNotIn(cpu_i5.name, lead.name)

        # Check product_info
        self.assertIn(
            f"<b>{cpu_i5.attribute_id.name}</b>: {cpu_i5.name}",
            lead.product_info,
        )

        # Check product_info_with_title
        self.assertIn(lead.name, lead.product_info_with_title)
        self.assertIn(
            f"<b>{cpu_i5.attribute_id.name}</b>: {cpu_i5.name}",
            lead.product_info_with_title,
        )

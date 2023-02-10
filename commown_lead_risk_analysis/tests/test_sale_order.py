from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class SaleOrderTC(RentalSaleOrderTC):
    def setUp(self):
        super(SaleOrderTC, self).setUp()
        partner = self.env.ref("base.partner_demo_portal")
        tax = self.get_default_tax()

        self.team1 = self.env.ref("sales_team.salesteam_website_sales")
        self.stage1 = self.env["crm.stage"].create(
            {
                "team_id": self.team1.id,
                "name": "[stage: start] TEST",
            }
        )
        contract_tmpl1 = self._create_rental_contract_tmpl(
            1,
            contract_line_ids=[
                self._contract_line(
                    1, "1 month Fairphone premium", tax, specific_price=25.0
                ),
                self._contract_line(2, "1 month ##ACCESSORY##", tax),
            ],
        )
        self.product1 = self._create_rental_product(
            name="Fairphone Premium",
            list_price=60.0,
            rental_price=30.0,
            followup_sales_team_id=self.team1.id,
            property_contract_template_id=contract_tmpl1.id,
        )
        so_line1 = self._oline(self.product1, product_uom_qty=2)

        self.team2 = self.team1.copy({"name": "team2"})
        self.product2 = self.env["product.product"].create(
            {
                "name": "Install /e/OS",
                "type": "service",
                "followup_sales_team_id": self.team2.id,
            }
        )
        so_line2 = self._oline(self.product2, product_uom_qty=3)

        self.team3 = self.team1.copy({"name": "team3"})
        self.product3 = self._create_rental_product(
            name="Phone protection",
            list_price=2.0,
            rental_price=1.0,
            followup_sales_team_id=self.team3.id,
        )
        so_line3 = self._oline(self.product3, product_uom_qty=1)

        self.so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [so_line1, so_line2, so_line3],
            }
        )

    def test_create_risk_analysis_leads_with_contracts(self):

        old_leads = self.env["crm.lead"].search([])
        self.so.action_confirm()
        new_leads = self.env["crm.lead"].search([]) - old_leads

        so_line1, so_line2, so_line3 = self.so.order_line
        leads1 = new_leads.filtered(lambda l: l.team_id == self.team1)
        leads2 = new_leads.filtered(lambda l: l.team_id == self.team2)
        leads3 = new_leads.filtered(lambda l: l.team_id == self.team3)

        self.assertEqual(new_leads, leads1 | leads2 | leads3)
        self.assertEqual(len(leads1), 2)
        self.assertEqual(len(leads2), 3)
        self.assertEqual(len(leads3), 1)
        self.assertEqual(leads1.mapped("stage_id"), self.stage1)
        self.assertFalse(leads2.mapped("stage_id"))
        self.assertEqual(leads1.mapped("so_line_id"), so_line1)
        self.assertEqual(leads2.mapped("so_line_id"), so_line2)
        self.assertEqual(leads3.mapped("so_line_id"), so_line3)

        self.assertEqual(
            sorted(leads1.mapped("contract_id.name")),
            ["%s-01" % self.so.name, "%s-02" % self.so.name],
        )

        self.assertFalse(leads2.mapped("contract_id"))
        self.assertEqual(
            sorted(leads2.mapped("name")),
            ["[%s-00/%d] Install /e/OS" % (self.so.name, i) for i in (1, 2, 3)],
        )

        self.assertTrue(leads3.contract_id)

    def test_create_risk_analysis_leads_without_contracts(self):
        "Also create RA leads for orphan products, ie when no contract was created"

        rental_so_line = self._oline(self.product3, product_uom_qty=2)
        service_so_line = self._oline(self.product2, product_uom_qty=1)
        partner = self.env.ref("base.partner_demo_portal")
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [rental_so_line, service_so_line],
            }
        )

        old_leads = self.env["crm.lead"].search([])
        so.action_confirm()
        new_leads = self.env["crm.lead"].search([]) - old_leads

        leads2 = new_leads.filtered(lambda l: l.team_id == self.team2)
        leads3 = new_leads.filtered(lambda l: l.team_id == self.team3)

        self.assertEqual(new_leads, leads2 | leads3)
        self.assertEqual(len(leads2), 1)
        self.assertEqual(len(leads3), 2)

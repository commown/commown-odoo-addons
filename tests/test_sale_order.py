from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class SaleOrderTC(RentalSaleOrderTC):

    def setUp(self):
        super(SaleOrderTC, self).setUp()
        partner = self.env.ref("portal.demo_user0_res_partner")
        tax = self.get_default_tax()

        self.team1 = self.env.ref("sales_team.salesteam_website_sales")
        self.stage1 = self.env["crm.stage"].create({
            "team_id": self.team1.id,
            "name": u"[stage: start] TEST",
        })
        contract_tmpl1 = self._create_rental_contract_tmpl(
            1, recurring_invoice_line_ids=[
                self._invoice_line(1, "1 month Fairphone premium", tax,
                                   specific_price=25.),
                self._invoice_line(2, "1 month ##ACCESSORY##", tax),
                ])
        product1 = self._create_rental_product(
            name="Fairphone Premium", list_price=60., rental_price=30.,
            followup_sales_team_id=self.team1.id,
            contract_template_id=contract_tmpl1.id)
        so_line1 = self._oline(product1, product_uom_qty=2)

        self.team2 = self.team1.copy({"name": u"team2"})
        product2 = self.env["product.product"].create({
            "name": u"Install /e/OS",
            "type": u"service",
        })
        product2.followup_sales_team_id = self.team2.id
        so_line2 = self._oline(product2, product_uom_qty=1)

        self.so = self.env["sale.order"].create({
            "partner_id": partner.id,
            "partner_invoice_id": partner.id,
            "partner_shipping_id": partner.id,
            "order_line": [so_line1, so_line2],
        })

    def test_create_risk_analysis_leads(self):

        old_leads = self.env["crm.lead"].search([])
        self.so.action_confirm()
        new_leads = self.env["crm.lead"].search([]) - old_leads

        so_line1, so_line2 = self.so.order_line
        leads1 = new_leads.filtered(lambda l: l.team_id==self.team1)
        leads2 = new_leads.filtered(lambda l: l.team_id==self.team2)

        self.assertEqual(new_leads, leads1 | leads2)
        self.assertEqual(len(leads1), 2)
        self.assertEqual(len(leads2), 1)
        self.assertEqual(leads1.mapped('stage_id'), self.stage1)
        self.assertEqual(leads2.mapped('stage_id'), self.env['crm.stage'])
        self.assertEqual(leads1.mapped("so_line_id"), so_line1)
        self.assertEqual(leads2.so_line_id, so_line2)

        self.assertEqual(sorted(leads1.mapped("contract_id.name")),
                         [u"%s-01" % self.so.name, u"%s-02" % self.so.name])
        self.assertFalse(leads2.contract_id)
        self.assertEqual(leads2.name, u"[%s-00] Install /e/OS" % self.so.name)

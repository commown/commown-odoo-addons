from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class ContractSaleWithCouponTC(RentalSaleOrderTC):
    def setUp(self):
        super(ContractSaleWithCouponTC, self).setUp()
        partner = self.env.ref("base.res_partner_3")

        self.campaign = self.env["coupon.campaign"].create(
            {
                "name": "test-campaign",
                "seller_id": 1,
            }
        )

        contract_tmpl = self._create_rental_contract_tmpl(
            1,
            contract_line_ids=[
                self._contract_line(1, "PC rental", specific_price=30.0)
            ],
        )

        iline = contract_tmpl.contract_line_ids[0]

        self.env["contract.template.discount.line"].create(
            {
                "name": "Test coupon discount: 80% first 3 months!",
                "amount_value": 80.0,
                "amount_type": "percent",
                "start_reference": "date_start",
                "end_reference": "date_start",
                "start_type": "relative",
                "start_value": 0,
                "start_unit": "months",
                "end_type": "relative",
                "end_value": 3,
                "end_unit": "months",
                "contract_template_line_id": iline.id,
                "condition": "coupon_from_campaign",
                "coupon_campaign_id": self.campaign.id,
            }
        )

        product = self._create_rental_product(
            name="Fairphone Premium",
            list_price=60.0,
            rental_price=30.0,
            property_contract_template_id=contract_tmpl.id,
        )

        self.so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [self._oline(product)],
            }
        )

        self.coupon = self.env["coupon.coupon"].create(
            {
                "code": "TEST-CODE",
                "campaign_id": self.campaign.id,
                "used_for_sale_id": self.so.id,
            }
        )

        self.so.action_confirm()

        self.contract = self.env["contract.contract"].of_sale(self.so)
        self.contract.ensure_one()

from odoo.addons.contract.tests.test_contract import TestContractBase

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class DiscountLineTC(TestContractBase):

    def setUp(self):
        super(DiscountLineTC, self).setUp()
        self.contract.is_auto_pay = False

    def test_no_issue_condition(self):
        self.env['contract.discount.line'].create({
            "name": u"Fix discount",
            "amount_type": u"fix",
            "amount_value": 5.,
            "contract_line_id": self.acct_line.id,
            "condition": u"no_issue_to_date",
        })

        # Test without penalty
        self.assertFalse(self.contract.contractual_issue_ids)
        self.contract.contractual_issue_ids |= self.env['project.task'].create({
            "name": u"task1",
            "penalty_exemption": True,
            "contractual_issue_date": self.contract.date_start,
        })

        inv1 = self.contract.recurring_create_invoice()
        self.assertEqual(inv1.mapped("invoice_line_ids.discount"), [5.])

        # Add a penalty
        self.contract.contractual_issue_ids |= self.env['project.task'].create({
            "name": u"task2",
            "penalty_exemption": False,
            "contractual_issue_date": self.contract.date_start,
        })

        inv2 = self.contract.recurring_create_invoice()
        self.assertEqual(inv2.mapped("invoice_line_ids.discount"), [0.])

    def test_min_end_contract_date(self):
        self.contract.update({
            'min_contract_duration': 2,
            'recurring_rule_type': 'monthly',
            'recurring_interval': 1,
        })

        self.env['contract.discount.line'].create({
            "name": u"Post commitment discount",
            "amount_type": u"percent",
            "amount_value": 5.,
            "start_reference": "min_contract_end_date",
            "start_value": 1,
            "start_unit": "months",
            "end_type": "relative",
            "end_reference": "min_contract_end_date",
            "end_value": 4,
            "end_unit": "months",
            "contract_line_id": self.acct_line.id,
        })

        self.assertEqual(self.contract.min_contract_end_date, "2016-04-15")

        expected = [("2016-02-29", 0.), ("2016-03-29", 0.), ("2016-04-29", 0.),
                    ("2016-05-29", 5.), ("2016-06-29", 5.), ("2016-07-29", 5.),
                    ("2016-08-29", 0.), ("2016-09-29", 0.)]

        for date, discount in expected:
            inv = self.contract.recurring_create_invoice()
            self.assertEqual(inv.date_invoice, date)
            self.assertEqual(inv.mapped("invoice_line_ids.discount"),
                             [discount], "incorrect discount at %s" % date)


class CouponConditionTC(RentalSaleOrderTC):

    def test(self):
        partner = self.env.ref('portal.demo_user0_res_partner')

        campaign = self.env['coupon.campaign'].create({
            "name": u"test campaign",
            "seller_id": 1,
        })

        contract_tmpl = self._create_rental_contract_tmpl(
            1, recurring_invoice_line_ids=[
                self._invoice_line(1, 'PC rental', specific_price=30.)])

        iline = contract_tmpl.recurring_invoice_line_ids[0]

        self.env['contract.template.discount.line'].create({
            "name": u"Test coupon discount: 80% first 3 months!",
            "amount_value": 80., "amount_type": u"percent",
            "start_reference": "date_start",
            "end_reference": "date_start",
            "start_type": "relative", "start_value": 0, "start_unit": "months",
            "end_type": "relative", "end_value": 3, "end_unit": "months",
            "contract_template_line_id": iline.id,
            "condition": "coupon_from_campaign",
            "coupon_campaign_id": campaign.id,
        })

        product = self._create_rental_product(
            name='Fairphone Premium', list_price=60., rental_price=30.,
            contract_template_id=contract_tmpl.id)

        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [self._oline(product)],
        })

        coupon = self.env['coupon.coupon'].create({
            "code": u"TEST-CODE",
            "campaign_id": campaign.id,
            "used_for_sale_id": so.id,
        })

        so.action_confirm()

        contract = self.env['account.analytic.account'].search([
            ('name', 'ilike', '%' + so.name + '%'),
        ]).ensure_one()

        # Default tax is 15%
        self.assertEqual(contract.recurring_create_invoice().amount_total, 6.9)
        self.assertEqual(contract.recurring_create_invoice().amount_total, 6.9)
        self.assertEqual(contract.recurring_create_invoice().amount_total, 6.9)
        self.assertEqual(contract.recurring_create_invoice().amount_total, 34.5)

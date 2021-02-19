from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class CrmLeadTC(TransactionCase):

    def setUp(self):
        super(CrmLeadTC, self).setUp()
        self.lead = self.env['crm.lead'].create({
            'name': u'[SO99999-01] TEST',
            'partner_id': self.env.ref('base.res_partner_1').id,
            'type': 'opportunity',
            'team_id': self.env.ref('sales_team.salesteam_website_sales').id,
            'send_email_on_delivery': False,
        })

    def _link_lead_to_contract(self):
        "Create a contract link to the lead by its (sale order like) name"
        return self.env['contract.contract'].create({
            'name': u'SO99999-01',
            'is_auto_pay': False,
            'recurring_next_date': '2030-01-01',
            'partner_id': self.lead.partner_id.id,
        })

    def test_actions_on_delivery_start_contract(self):

        self.assertTrue(self.lead.start_contract_on_delivery)
        contract = self._link_lead_to_contract()

        # Simulate delivery
        self.lead.delivery_date = '2018-01-01'

        # Check results: contract started
        self.assertTrue(contract.is_auto_pay)
        self.assertTrue(all(l.startswith('2018-01-01')
                            for l in contract.contract_line_ids))

    def test_actions_on_delivery_no_start_contract(self):

        self.lead.start_contract_on_delivery = False
        contract = self._link_lead_to_contract()

        # Simulate delivery
        self.lead.delivery_date = '2018-01-01'

        # Check results: contract not started
        self.assertFalse(contract.is_auto_pay)

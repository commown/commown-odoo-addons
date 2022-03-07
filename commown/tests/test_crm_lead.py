from datetime import date

from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class CrmLeadTC(TransactionCase):

    def setUp(self):
        super(CrmLeadTC, self).setUp()
        self.team = self.env.ref('sales_team.salesteam_website_sales')
        self.team.default_perform_actions_on_delivery = True
        self.lead = self._add_lead(name='TEST LEAD',
                                   send_email_on_delivery=False)

    def _add_lead(self, **kwargs):
        kwargs.setdefault('name', 'TEST')
        kwargs.setdefault('team_id', self.team.id)
        kwargs.setdefault('partner_id',
                          self.env.ref('base.partner_demo_portal').id)
        kwargs.setdefault('type', 'opportunity')
        return self.env['crm.lead'].create(kwargs)

    def _create_contract(self):
        "Create a contract link to the lead by its (sale order like) name"
        return self.env['contract.contract'].create({
            'name': 'TEST CONTRACT',
            'is_auto_pay': False,
            'date_start': '2030-01-01',
            'recurring_next_date': '2030-01-01',
            'partner_id': self.lead.partner_id.id,
        })

    def test_default_no_action_on_delivery(self):
        team = self.lead.team_id

        team.default_perform_actions_on_delivery = False
        lead = self._add_lead(team_id=team.id)

        self.assertFalse(lead.send_email_on_delivery)
        self.assertFalse(lead.start_contract_on_delivery)

        team.default_perform_actions_on_delivery = True
        lead = self._add_lead(team_id=team.id)

        self.assertTrue(lead.send_email_on_delivery)
        self.assertTrue(lead.start_contract_on_delivery)

    def test_actions_on_delivery_start_contract(self):

        self.assertTrue(self.lead.start_contract_on_delivery)
        contract = self._create_contract()
        self.lead.contract_id = contract.id

        # Simulate delivery
        self.lead.delivery_date = date(2018, 1, 1)

        # Check results: contract started
        self.assertTrue(contract.is_auto_pay)
        self.assertEqual(contract.date_start, date(2018, 1, 1))

    def test_actions_on_delivery_no_start_contract(self):

        self.lead.start_contract_on_delivery = False
        contract = self._create_contract()
        self.lead.contract_id = contract.id

        # Simulate delivery
        self.lead.delivery_date = date(2018, 1, 1)

        # Check results: contract not started
        self.assertFalse(contract.is_auto_pay)

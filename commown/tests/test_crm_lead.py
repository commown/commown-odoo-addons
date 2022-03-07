from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class CrmLeadTC(TransactionCase):

    def setUp(self):
        super(CrmLeadTC, self).setUp()
        self.team = self.env.ref('sales_team.salesteam_website_sales')
        self.team.default_perform_actions_on_delivery = True
        self.lead = self._add_lead(name='[SO99999-01] TEST',
                                   send_email_on_delivery=False)

    def _add_lead(self, **kwargs):
        kwargs.setdefault('name', 'TEST')
        kwargs.setdefault('team_id', self.team.id)
        kwargs.setdefault('partner_id',
                          self.env.ref('portal.demo_user0_res_partner').id)
        kwargs.setdefault('type', 'opportunity')
        return self.env['crm.lead'].create(kwargs)

    def _link_lead_to_contract(self):
        "Create a contract link to the lead by its (sale order like) name"
        return self.env['account.analytic.account'].create({
            'name': 'SO99999-01',
            'recurring_invoices': True,
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
        contract = self._link_lead_to_contract()

        # Simulate delivery
        self.lead.delivery_date = '2018-01-01'

        # Check results: contract started
        self.assertTrue(contract.is_auto_pay)
        self.assertTrue(contract.date_start.startswith('2018-01-01'))

    def test_actions_on_delivery_no_start_contract(self):

        self.lead.start_contract_on_delivery = False
        contract = self._link_lead_to_contract()

        # Simulate delivery
        self.lead.delivery_date = '2018-01-01'

        # Check results: contract not started
        self.assertFalse(contract.is_auto_pay)

from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class CrmLeadTC(TransactionCase):

    def setUp(self):
        super(CrmLeadTC, self).setUp()
        portal_user = self.env['res.users'].create({
            'firstname': u'Flo', 'lastname': u'C', 'login': 'fc',
            'email': 'fc@test'})
        portal_partner = self.env['res.partner'].create({
            'firstname': u'Flo', 'lastname': u'C',
            'email': 'fc@test', 'phone': '+336999999999',
            'street': '2 rue de Rome', 'zip': '67000', 'city': 'Strasbourg',
            'country_id': self._country('FR').id,
            'user_ids': [(6, 0, [portal_user.id])]})
        self.lead = self.env['crm.lead'].create({
            'name': '[SO00000] Fake order',
            'partner_id': portal_partner.id,
            'type': 'opportunity',
            'team_id': self.env.ref('sales_team.salesteam_website_sales').id,
        })

    def _country(self, code):
        return self.env['res.country'].search([('code', '=', code)])

    def _link_lead_to_contract(self):
        "Create a contract link to the lead by its (sale order like) name"
        self.lead.name = u'[SO99999-02] TEST DELIVERY'
        return self.env['account.analytic.account'].create({
            'name': u'SO99999-02',
            'recurring_invoices': True,
            'is_auto_pay': False,
            'date_start': '2030-01-01',
            'recurring_next_date': '2030-01-01',
            'partner_id': self.lead.partner_id.id,
        })

    def _last_message(self):
        return self.env['mail.message'].search([
            ('res_id', '=', self.lead.id), ('model', '=', 'crm.lead')])[0]

    def test_actions_on_delivery_start_contract(self):

        # Check default schema values while we are here...
        self.assertTrue(self.lead.send_email_on_delivery)
        self.assertTrue(self.lead.start_contract_on_delivery)
        # # Avoid a partner name_create call for the from email template field
        # # (which crashes slimpay module's firstname check)
        # self.env.user.company_id.email = 'webmaster@commown.fr'

        contract = self._link_lead_to_contract()

        # Simulate delivery with MYSTATUS status and a (fake) pre-registered
        # mail template, created for that occasion:
        template = self.env.ref('commown.mail_template_lead_start_error').copy(
            {'subject': 'MYSTATUS test', 'email_to': False})
        lead = self.lead.with_context(
            {'UNITTEST_TEMPLATE_IDS': {'MYSTATUS': template.id}})
        lead.expedition_status = u'[MYSTATUS] Test with registered template'
        lead.delivery_date = '2018-01-01'

        # Check results: contract started and email sent
        self.assertTrue(contract.is_auto_pay)
        self.assertTrue(contract.date_start.startswith('2018-01-01'))
        last_message = self._last_message()
        self.assertEqual(last_message.subject, u'MYSTATUS test')
        self.assertEqual(last_message.message_type, 'notification')

    def test_actions_on_delivery_no_start_contract_and_error_mail(self):

        self.assertTrue(self.lead.send_email_on_delivery)
        self.lead.start_contract_on_delivery = False

        contract = self._link_lead_to_contract()

        # Simulate delivery with unknown status
        self.lead.update({
            'expedition_status': u'[ERROR] Test error mail template',
            'delivery_date': '2018-01-01',
        })

        # Check results: contract not started and error email sent
        self.assertFalse(contract.is_auto_pay)
        last_message = self._last_message()

        self.assertEqual(
            last_message.subject,
            u'[Commown] ERROR starting crm.lead id %s' % self.lead.id)
        self.assertEqual(last_message.message_type, 'email')

        self.assertIn(
            u'Expedition status does not contain a code associated with'
            u' a contract start email template.',
            last_message.body)

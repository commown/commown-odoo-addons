import os.path as osp
import json
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import encoders
from datetime import datetime
from base64 import b64decode

import requests
import mock

from odoo.exceptions import MissingError
from odoo.tests.common import TransactionCase, at_install, post_install

from odoo.addons.commown.models.colissimo_utils import shipping_data


HERE = osp.dirname(__file__)


class FakeResponse(object):

    def __init__(self, json_data, pdf_data):
        self.json_data = json_data
        self.pdf_data = pdf_data
        self.headers, self.content = self._build()

    def raise_for_status(self):
        pass

    def _build(self):
        msg = MIMEMultipart()

        json_part = MIMEBase('application', 'json')
        json_part.set_payload(json.dumps(self.json_data))
        msg.attach(json_part)

        pdf_part = MIMEBase('application', 'octet-stream')
        pdf_part.set_payload(self.pdf_data)
        encoders.encode_base64(pdf_part)
        msg.attach(pdf_part)

        msg_text = msg.as_string()
        boundary = msg.get_boundary()
        headers = {'Content-Type': 'multipart/mixed; boundary="%s"'
                   % boundary}
        part_marker = '--' + boundary
        content = part_marker + msg_text.split(part_marker, 1)[1]
        return headers, content


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
        with open(osp.join(HERE, 'fake_label.pdf')) as fobj:
            self.fake_label_data = fobj.read()
        self.fake_colissimo_data = {
            'colissimo_login': 'ColissimoLogin',
            'colissimo_password': 'ColissimoPassword',
            'colissimo_sender_email': 'test@test.com',
            'colissimo_commercial_name': 'CommercialName',
        }

    def _country(self, code):
        return self.env['res.country'].search([('code', '=', code)])

    def test_shipping_data_product_code(self):
        base_args = [self.env['res.partner'], self.lead.partner_id,
                     'SO00000', 'Commown']

        # French label
        data = shipping_data(*base_args)
        self.assertEqual(data['letter']['service']['productCode'], 'DOS')

        # French return label
        data = shipping_data(*(base_args + [True]))
        self.assertEqual(data['letter']['service']['productCode'], 'CORE')

        # International label
        self.lead.partner_id.country_id = self._country('BE')
        data = shipping_data(*base_args)
        self.assertEqual(data['letter']['service']['productCode'], 'COLI')

        # International Return label
        self.lead.partner_id.country_id = self._country('BE')
        data = shipping_data(*(base_args + [True]))
        self.assertEqual(data['letter']['service']['productCode'], 'CORI')

    def test_create_colissimo_fairphone_label(self):
        fake_meta_data = {'labelResponse': {'parcelNumber': '6X0000000000'}}
        self.fake_resp = FakeResponse(fake_meta_data, self.fake_label_data)

        lead = self.lead.with_context(self.fake_colissimo_data)
        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            lead._create_colissimo_fairphone_label()

        self.assertEqual(lead.expedition_ref, '6X0000000000')
        self.assertEqual(lead.expedition_date,
                         datetime.today().strftime('%Y-%m-%d'))
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id),
            ])
        self.assertEqual(len(attachments), 1)
        att = attachments[0]
        self.assertEqual(att.datas_fname, '6X0000000000.pdf')
        self.assertEqual(att.name, 'colissimo.pdf')
        if b64decode(att.datas) != self.fake_label_data:
            self.fail('incorrect pdf label')

    def test_create_colissimo_fairphone_return_label(self):
        " Only check the `ship` function was called with the right arguments. "
        fake_meta_data = {'labelResponse': {'parcelNumber': '8R0000000000'}}

        colissimo_data = self.fake_colissimo_data.copy()
        colissimo_data['colissimo_is_return'] = True
        lead = self.lead.with_context(colissimo_data)
        with mock.patch(
                'odoo.addons.commown.models.crm_lead.ship',
                return_value=(fake_meta_data, 'xxx')) as mocked_ship:
            lead._create_colissimo_fairphone_label()

        self.assertEqual(lead.expedition_ref, '8R0000000000')
        self.assertEqual(mocked_ship.call_count, 1)
        # Sender is lead partner
        self.assertEqual(mocked_ship.call_args[0][2], self.lead.partner_id)
        # is_return argument is True
        self.assertIs(mocked_ship.call_args[0][6], True)

    def test_colissimo_fairphone_label_and_update(self):
        fake_meta_data = {'labelResponse': {'parcelNumber': '6X0000000000'}}
        self.fake_resp = FakeResponse(fake_meta_data, self.fake_label_data)

        lead = self.lead.with_context(self.fake_colissimo_data)
        assert lead.expedition_ref is False
        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            att1 = lead.colissimo_fairphone_label()
            self.assertEqual(att1.datas_fname, '6X0000000000.pdf')
            self.assertEqual(lead.expedition_ref, '6X0000000000')

            att2 = lead.colissimo_fairphone_label()
            self.assertEqual(att1, att2)

            lead.write({'expedition_ref': ''})
            with self.assertRaises(MissingError):
                att1.name

    def test_colissimo_fairphone_labels(self):
        leads = self.env['crm.lead']
        for num in range(5):
            ctx = {'num': num}
            lead = self.lead.copy(
                {'name': '[SO%(num)05d] Lead num %(num)d' % ctx}
            ).with_context(self.fake_colissimo_data)

            fake_meta_data = {'labelResponse': {
                'parcelNumber': '6X%(num)010d' % ctx}}
            fake_resp = FakeResponse(fake_meta_data, self.fake_label_data)

            with mock.patch.object(requests, 'post', return_value=fake_resp):
                lead._create_colissimo_fairphone_label()

            leads += lead

        all_labels = leads.colissimo_fairphone_labels()
        self.assertEqual(all_labels.name, 'colissimo.pdf')

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

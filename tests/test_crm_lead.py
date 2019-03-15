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

from odoo.addons.commown_shipping.models.colissimo_utils import shipping_data


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
        self.env['keychain.account'].create({
            'namespace': 'colissimo',
            'name': 'Colissimo standard',
            'technical_name': 'colissmo-std',
            'login': 'ColissimoLogin',
            'clear_password': 'test',
        })
        self.fake_colissimo_data = {
            'colissimo_account': 'ColissimoLogin',
            'colissimo_sender_email': 'test@test.com',
            'colissimo_weight': 0.5,
        }

    def _country(self, code):
        return self.env['res.country'].search([('code', '=', code)])

    def test_shipping_data_product_code(self):
        base_kwargs = {
            'sender': self.env['res.partner'],
            'recipient': self.lead.partner_id,
            'order_number': u'SO00000',
            'commercial_name': u'Commown',
            'weight': 0.5,
        }

        # French label
        data = shipping_data(**base_kwargs)
        self.assertEqual(data['letter']['service']['productCode'], 'DOS')

        # French return label
        data = shipping_data(is_return=True, **base_kwargs)
        self.assertEqual(data['letter']['service']['productCode'], 'CORE')

        # International label
        self.lead.partner_id.country_id = self._country('BE')
        data = shipping_data(**base_kwargs)
        self.assertEqual(data['letter']['service']['productCode'], 'COLI')

        # International Return label
        self.lead.partner_id.country_id = self._country('BE')
        data = shipping_data(is_return=True, **base_kwargs)
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
                'odoo.addons.commown_shipping.models.crm_lead.ship',
                return_value=(fake_meta_data, 'xxx')) as mocked_ship:
            lead._create_colissimo_fairphone_label()

        self.assertEqual(lead.expedition_ref, '8R0000000000')
        self.assertEqual(mocked_ship.call_count, 1)
        # Sender is lead partner
        kwargs = mocked_ship.call_args[1]
        self.assertEqual(kwargs['sender'], self.lead.partner_id)
        # is_return argument is True
        self.assertIs(kwargs['is_return'], True)

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

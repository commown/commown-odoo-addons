import os.path as osp
import json
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import encoders
from datetime import datetime
from base64 import b64decode
from StringIO import StringIO

import requests
import mock
from PyPDF2 import PdfFileReader  # how to declare test dependencies in odoo?

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
        self.shipping_account = self.env['keychain.account'].create({
            'namespace': 'colissimo',
            'name': 'Colissimo standard',
            'technical_name': 'colissmo-std',
            'login': 'ColissimoLogin',
            'clear_password': 'test',
        })
        self.parcel_type = self.env['commown.parcel.type'].create({
            'name': 'fp2-ins450', 'weight': 0.5, 'insurance_value': 450,
        })

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

    def test_create_parcel_label(self):
        fake_meta_data = {'labelResponse': {'parcelNumber': '6X0000000000'}}
        self.fake_resp = FakeResponse(fake_meta_data, self.fake_label_data)
        lead = self.lead

        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            lead._create_parcel_label(self.parcel_type.name,
                                      self.shipping_account.login,
                                      self.env['res.partner'],  # empty sender!
                                      lead.partner_id,
                                      lead.get_label_ref())

        self.assertEqual(lead.expedition_ref, '6X0000000000')
        self.assertEqual(lead.expedition_date,
                         datetime.today().strftime('%Y-%m-%d'))
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id),
            ])
        self.assertEqual(len(attachments), 1)
        att = attachments[0]
        self.assertEqual(att.datas_fname, '6X0000000000.pdf')
        self.assertEqual(att.name, self.parcel_type.name + '.pdf')
        if b64decode(att.datas) != self.fake_label_data:
            self.fail('incorrect pdf label')

    def test_parcel_labels(self):
        leads = self.env['crm.lead']
        base_args = [self.parcel_type.name,
                     self.shipping_account.login,
                     self.env['res.partner'],  # empty sender!
                     self.lead.partner_id,
                     ]

        for num in range(5):
            ctx = {'num': num}
            lead = self.lead.copy({'name': '[SO%(num)05d] Lead %(num)d' % ctx})

            fake_meta_data = {'labelResponse': {
                'parcelNumber': '6X%(num)010d' % ctx}}
            fake_resp = FakeResponse(fake_meta_data, self.fake_label_data)
            args = base_args + [lead.get_label_ref()]

            with mock.patch.object(requests, 'post', return_value=fake_resp):
                lead._get_or_create_label(*args)

            leads += lead

        all_labels = leads.parcel_labels(*base_args)

        self.assertEqual(all_labels.name, self.parcel_type.name + '.pdf')
        pdf = PdfFileReader(StringIO(b64decode(all_labels.datas)))
        self.assertEqual(pdf.getNumPages(), 2)

        lead = self.lead.copy({'name': '[Test single]'})
        with mock.patch.object(requests, 'post', return_value=fake_resp):
            label = lead.parcel_labels(*base_args, force_single=True)

        self.assertEqual((b64decode(label.datas)), self.fake_label_data)

from datetime import datetime

import requests
import mock

from odoo.addons.commown_shipping.models.colissimo_utils import shipping_data

from odoo.tests.common import at_install, post_install

from .common import BaseShippingTC, pdf_page_num


@at_install(False)
@post_install(True)
class CrmLeadTC(BaseShippingTC):

    def setUp(self):
        super(CrmLeadTC, self).setUp()
        portal_partner = self.env.ref('portal.demo_user0_res_partner')
        self.lead = self.env['crm.lead'].create({
            'name': '[SO00000] Fake order',
            'partner_id': portal_partner.id,
            'type': 'opportunity',
            'team_id': self.env.ref('sales_team.salesteam_website_sales').id,
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
        self.lead.partner_id.country_id = self._country('FR')
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
        lead = self.lead

        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            lead._create_parcel_label(self.parcel_type,
                                      self.shipping_account,
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
        self.assertEqualFakeLabel(att)

    def test_parcel_labels(self):
        leads = self.env['crm.lead']
        base_args = [self.parcel_type,
                     self.shipping_account,
                     self.env['res.partner'],  # empty sender!
                     self.lead.partner_id,
                     ]

        for num in range(5):
            lead = self.lead.copy({'name': '[SO%05d] Test lead' % num})
            args = base_args + [lead.get_label_ref()]

            with mock.patch.object(
                    requests, 'post', return_value=self.fake_resp):
                lead._get_or_create_label(*args)
            leads += lead

        all_labels = leads.parcel_labels(
            self.parcel_type.technical_name,
            self.shipping_account.technical_name,
            self.env['res.partner'],  # empty sender!
            )

        self.assertEqual(all_labels.name, self.parcel_type.name + '.pdf')
        self.assertEqual(pdf_page_num(all_labels), 2)

        lead = self.lead.copy({'name': '[Test single]'})
        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            label = lead.parcel_labels(
                self.parcel_type.technical_name,
                self.shipping_account.technical_name,
                self.env['res.partner'],
                force_single=True)

        self.assertEqualFakeLabel(label)

from datetime import datetime
from urlparse import urlparse

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
        product = self.env['product.product'].create({
            'name': u'Fairphone',
            'shipping_parcel_type_id': self.parcel_type.id,
        })
        team = self.env.ref('sales_team.salesteam_website_sales')
        team.update({'shipping_account_id': self.shipping_account.id})

        so = self.env['sale.order'].create({
            'partner_id': portal_partner.id,
            'partner_invoice_id': portal_partner.id,
            'partner_shipping_id': portal_partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'name': product.name,
                'product_uom_qty': 1,
                'price_unit': product.list_price,
            })],
        })

        self.lead = self.env['crm.lead'].create({
            'name': '[SO00000] Fake order',
            'partner_id': portal_partner.id,
            'type': 'opportunity',
            'team_id': team.id,
            'so_line_id': so.order_line[0].id,
        })

    def _country(self, code):
        return self.env['res.country'].search([('code', '=', code)])

    def _attachment_from_download_action(self, download_action):
        return self.env['ir.attachment'].browse(
            int(urlparse(download_action['url']).path.rsplit('/', 1)[-1]))

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

    def test_print_parcel_action(self):
        leads = self.env['crm.lead']
        for num in range(5):
            leads += self.lead.copy({'name': '[SO%05d] Test lead' % num})

        act = self.env.ref('commown_shipping.action_print_outward_label_lead')

        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            download_action = act.with_context({
                'active_model': leads._name, 'active_ids': leads.ids}).run()

        all_labels = self._attachment_from_download_action(download_action)
        self.assertEqual(all_labels.name, self.parcel_type.name + '.pdf')
        self.assertEqual(pdf_page_num(all_labels), 2)

from datetime import datetime

import requests
import mock

from odoo.exceptions import UserError

from odoo.addons.commown_shipping.models.colissimo_utils import shipping_data

from odoo.tests.common import TransactionCase, at_install, post_install

from .common import BaseShippingTC, pdf_page_num


@at_install(False)
@post_install(True)
class CrmLeadShippingTC(BaseShippingTC):

    def setUp(self):
        super(CrmLeadShippingTC, self).setUp()

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

    def _print_outward_labels(self, leads):
        act = self.env.ref('commown_shipping.action_print_outward_label_lead')

        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            return act.with_context({
                'active_model': leads._name, 'active_ids': leads.ids}).run()

    def test_shipping_data_address_too_long(self):
        """ When a partner has a too long address, a user error is raised
        with its name (useful when printing several labels at once).
        """
        other_partner = self.lead.partner_id.copy({
            'street': u'x' * 100,
        })
        other_partner.name = u'John TestAddressTooLong'

        leads = self.env['crm.lead']
        for num in range(5):
            leads += self.lead.copy({'name': '[SO%05d] Test lead' % num})
            if num == 3:
                leads[-1].partner_id = other_partner

        with self.assertRaises(UserError) as err:
            self._print_outward_labels(leads)
        self.assertEqual(err.exception.name,
                         u'Address too long for "John TestAddressTooLong"')

    def test_shipping_data_empty_name(self):
        self.lead.partner_id.firstname = False
        data = shipping_data(
            sender=self.env['res.partner'],
            recipient=self.lead.partner_id,
            order_number= u'SO00000',
            commercial_name=u'Commown',
            weight=0.5,
        )
        self.assertEqual(data['letter']['addressee']['address']['firstName'],
                         '')

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

        download_action = self._print_outward_labels(leads)

        all_labels = self._attachment_from_download_action(download_action)
        self.assertEqual(all_labels.name, self.parcel_type.name + '.pdf')
        self.assertEqual(pdf_page_num(all_labels), 2)


@at_install(False)
@post_install(True)
class CrmLeadDeliveryTC(TransactionCase):

    def setUp(self):
        super(CrmLeadDeliveryTC, self).setUp()
        team = self.env.ref('sales_team.salesteam_website_sales')
        team.update({
            'used_for_shipping': True,
            'on_delivery_email_template_id': self.env.ref(
                'commown_shipping.delivery_email_example').id,
            'default_perform_actions_on_delivery': True,
        })
        self.lead = self.env['crm.lead'].create({
            'name': u'[SO99999-01] TEST DELIVERY',
            'partner_id': self.env.ref('portal.demo_user0_res_partner').id,
            'type': 'opportunity',
            'team_id': team.id,
        })

    def _last_message(self):
        return self.env['mail.message'].search([
            ('res_id', '=', self.lead.id), ('model', '=', 'crm.lead')])[0]

    def check_mail_delivered(self, subject, code):
        last_message = self._last_message()
        self.assertEqual(last_message.message_type, 'notification')
        self.assertEqual(last_message.subject, subject)
        self.assertIn(u'code: %s' % code, last_message.body)
        return last_message

    def test_delivery_email_template(self):
        # Shipping deactivated, template set => None expected
        self.lead.team_id.used_for_shipping = False
        assert self.lead.team_id.on_delivery_email_template_id, (
            'test prerequisite error')
        self.assertIsNone(self.lead.delivery_email_template())

        # Shipping activated, no lead custom template => custom expected
        self.lead.team_id.used_for_shipping = True
        self.lead.on_delivery_email_template_id = False
        self.assertEqual(self.lead.delivery_email_template(),
                         self.lead.team_id.on_delivery_email_template_id)

        # Shipping activated, custom template => custom expected
        self.lead.on_delivery_email_template_id = \
            self.lead.team_id.on_delivery_email_template_id.copy().id
        self.assertEqual(self.lead.delivery_email_template().name,
                         u'Post-delivery email (copy)')

        # Shipping deactivated, even with custom template => None expected
        self.lead.team_id.used_for_shipping = False
        self.assertIsNone(self.lead.delivery_email_template())

    def test_actions_on_delivery_send_email_team_template(self):

        self.assertTrue(self.lead.send_email_on_delivery)

        # Simulate delivery
        self.lead.expedition_status = u'[LIVCFM] Test'
        self.lead.delivery_date = '2018-01-01'

        # Check result
        self.check_mail_delivered(u'Product delivered', 'LIVCFM')

    def test_actions_on_delivery_send_email_no_status(self):
        " Check empty expedition status is OK "

        self.assertTrue(self.lead.send_email_on_delivery)

        # Simulate delivery
        self.lead.expedition_status = False
        self.lead.delivery_date = '2018-01-01'

        # Check result
        self.check_mail_delivered(u'Product delivered', 'EMPTY_CODE')

    def test_actions_on_delivery_send_email_custom_template(self):

        self.assertTrue(self.lead.send_email_on_delivery)

        self.lead.on_delivery_email_template_id = \
            self.lead.team_id.on_delivery_email_template_id.copy({
                'subject': u'Test custom email',
                'body': u'coucou'
            }).id

        # Simulate delivery
        self.lead.expedition_status = u'[LIVGAR] Test'
        self.lead.delivery_date = '2018-01-01'

        # Check result
        self.check_mail_delivered(u'Test custom email', 'LIVGAR')

    def test_actions_on_delivery_send_email_no_template(self):
        " A user error must be raised in the case no template was specified "

        self.assertTrue(self.lead.send_email_on_delivery)
        self.lead.on_delivery_email_template_id = False
        self.lead.team_id.on_delivery_email_template_id = False

        # Simulate delivery
        self.assertRaises(UserError,
                          self.lead.update, {'delivery_date': '2018-01-01'})

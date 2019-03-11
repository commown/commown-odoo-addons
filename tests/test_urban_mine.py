import os.path as osp
from base64 import b64decode

import mock

from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class TestRegistration(TransactionCase):

    def setUp(self):
        super(TestRegistration, self).setUp()
        self.team = self.env.ref('urban_mine.urban_mine_managers')
        self.partner = self.env['res.partner'].create({
            'name': 'Elie A',
            'email': 'contact@commown.fr',
            'street': '2 rue de Rome',
            'zip': '67000',
            'city': 'Strasbourg',
            'country_id': self.env.ref('base.fr').id,
            'supplier': True,
            'from_urban_mine': True,
        })

    def get_leads(self, partner_id):
        return self.env['crm.lead'].search([
            ('team_id', '=', self.team.id),
            ('partner_id', '=', partner_id),
        ])

    def test_opportunity_creation(self):
        self.assertEqual(len(self.get_leads(self.partner.id)), 1)

    def test_opportunity_ok_send_label(self):
        lead = self.get_leads(self.partner.id)

        fake_meta_data = {'labelResponse': {'parcelNumber': '8R0000000000'}}
        with open(osp.join(osp.dirname(__file__), 'fake_label.pdf')) as fobj:
            fake_label_data = fobj.read()

        lead = lead.with_context({
            'colissimo_login': 'ColissimoLogin',
            'colissimo_password': 'ColissimoPassword',
            'colissimo_sender_email': 'test@test.com',
            'colissimo_commercial_name': 'CommercialName',
            'colissimo_is_return': True,
            'colissimo_force_single_label': True,
        })
        with mock.patch(
                'odoo.addons.commown_shipping.models.crm_lead.ship',
                return_value=(fake_meta_data, fake_label_data)) as mocked_ship:
            lead.update({'stage_id': self.env.ref('urban_mine.stage2')})

        # Check a return label was created:
        # - the expedition reference is set on the lead
        # - the `is_return` arg of the ship function call was `True`
        self.assertEqual(mocked_ship.call_count, 1)
        self.assertIs(mocked_ship.call_args[0][6], True)
        # A message attached to the lead was sent, with the PDF attached
        self.assertTrue(lead.message_ids)
        last_note_msg = [
            m for m in lead.message_ids
            if m.subtype_id.get_xml_id().values() == ["mail.mt_comment"]][0]
        attachment = last_note_msg.attachment_ids
        self.assertEqual(len(attachment), 1)
        self.assertEqual(attachment.mimetype, 'application/pdf')
        self.assertEqual(b64decode(last_note_msg.attachment_ids.datas),
                         fake_label_data)

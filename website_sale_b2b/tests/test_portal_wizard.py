from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class PortalWizardTC(TransactionCase):
    def test(self):
        partner = self.env.ref("base.partner_demo_portal")
        self.assertTrue(partner.user_ids)

        website = self.env["website"].browse(1)
        partner.website_id = website.id

        wizard_model = self.env["portal.wizard"]

        wizard = wizard_model.with_context(active_ids=partner.ids).create({})
        self.assertEqual(len(wizard.user_ids), 1)
        self.assertTrue(wizard.user_ids[0].website_id, website)
        self.assertTrue(wizard.user_ids[0].had_user)

        partner2 = partner.copy({"website_id": False})
        self.assertFalse(partner2.user_ids)

        wizard = wizard_model.with_context(active_ids=partner2.ids).create({})
        self.assertEqual(len(wizard.user_ids), 1)
        self.assertFalse(wizard.user_ids[0].website_id)
        self.assertFalse(wizard.user_ids[0].had_user)

        wizard.user_ids[0].update({"website_id": website.id, "in_portal": True})
        wizard.action_apply()

        self.assertTrue(partner2.user_ids)
        self.assertEqual(partner2.user_ids[0].website_id, website)

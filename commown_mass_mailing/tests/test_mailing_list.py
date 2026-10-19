from odoo.tests import TransactionCase


class CommownMailingListCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"].load_lang("fr_FR")

        cls.list_generic = cls.env.ref("commown_mass_mailing.newsletter_generic")
        cls.list_customers = cls.env.ref("commown_mass_mailing.newsletter_customers")

        cls.partner_1, cls.partner_2 = cls.env["res.partner"].create(
            [
                {"name": "Partner 1", "email": "p1@test.com", "lang": "fr_FR"},
                {"name": "Partner 2", "email": "p2@test.com", "lang": "fr_FR"},
            ]
        )

    def _create_contact(self, partner, mailing_list):
        return (
            self.env["mailing.contact"]
            .with_context(default_list_ids=mailing_list.ids)
            .create({"name": partner.name, "email": partner.email})
        )

    def _create_and_confirm_sale(self, partner):
        "Create a basic sale to indicate a partner is a customer"
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner_1.id,
                "date_order": "2026-01-10",
            }
        )
        sale.action_confirm()
        return sale


class CommownMailingListTC(CommownMailingListCommon):
    def test_synchronize_generic_customer_lists(self):
        """
        Once a customer gets added to the customer mailing list,
        they should be removed from the generic mailing list
        """
        contact_1 = self._create_contact(self.partner_1, self.list_generic)
        contact_2 = self._create_contact(self.partner_2, self.list_generic)
        contacts = contact_1 | contact_2

        self.list_customers.action_sync()

        self.assertTrue(
            all(contact in self.list_generic.contact_ids for contact in contacts)
        )
        self.assertFalse(
            any(contact in self.list_customers.contact_ids for contact in contacts)
        )

        self._create_and_confirm_sale(self.partner_1)
        self.list_customers.action_sync()

        contact_1.invalidate_recordset()
        self.assertIn(contact_1, self.list_customers.contact_ids)
        self.assertNotIn(contact_1, self.list_generic.contact_ids)

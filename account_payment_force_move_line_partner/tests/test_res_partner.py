from odoo.tests import TransactionCase


class ForceMoveLinePartnerTC(TransactionCase):
    def test_name_get(self):
        """
        In the force partner wizard, the type of the partner should be displayed

        The display name shown on the web UI is queried from name_search, as display_name is a stored field on res.partner,
        and res.partner._compute_display_name overwrites any given context (see odoo/odoo/addons/base/models L349),
        As such, we use name_search to get the front-end result.
        """

        def get_display_name(queried_partner, in_wizard):
            Partner = self.env["res.partner"]
            Partner = Partner.with_context(in_force_aml_partner_wizard=in_wizard)
            return dict(Partner.name_search(queried_partner.name))[queried_partner.id]

        demo_partner = self.env.ref("base.partner_demo")
        field = demo_partner.fields_get("type", "selection")
        partner_types = dict(field["type"]["selection"])

        demo_partner.type = "contact"
        contact_type_name = partner_types["contact"]

        self.assertNotIn(contact_type_name, get_display_name(demo_partner, False))
        self.assertIn(contact_type_name, get_display_name(demo_partner, True))

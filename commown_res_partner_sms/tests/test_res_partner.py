from odoo.tests.common import SavepointCase


class ResPartnerSmsTC(SavepointCase):
    def test_get_mobile_phone(self):
        partner = self.env.ref("base.partner_demo")
        country = self.env.ref("base.fr")

        # Initialize Data
        # Make the partner french to ease readability of phones numbers (for us)
        partner.update(
            {
                "country_id": country.id,
                "mobile": False,
                "phone": False,
            }
        )

        # Test Pre-requisite
        self.assertFalse(partner.get_mobile_phone())

        # Test Results
        partner.update({"mobile": "0423232323"})
        self.assertFalse(partner.get_mobile_phone())

        partner.update({"phone": "0623232323"})
        self.assertEqual(partner.get_mobile_phone(), "0623232323")

        partner.update({"mobile": "+33733221100"})
        self.assertEqual(partner.get_mobile_phone(), "+33733221100")

        # If there is a country indicator in the number validity does not
        # depend on partner country
        partner.update({"country_id": self.env.ref("base.us").id})
        self.assertEqual(partner.get_mobile_phone(), "+33733221100")

        partner.update({"mobile": "0733221100"})
        self.assertFalse(partner.get_mobile_phone())

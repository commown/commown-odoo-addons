from .common import SponsoringTC


class SponsoringCampaignTC(SponsoringTC):
    def test_sponsor_code_unique_b2c(self):
        """
        When calling the sponsor campaign method two times on a partner (ie. starting a second contract),
        only one sponsor campaign should be created.
        """
        self.assertFalse(self.partner.sponsor_campaign_id)

        # First time
        self.partner._create_sponsor_campaign()

        campaign = self.partner.sponsor_campaign_id
        self.assertTrue(campaign)

        # Second time
        self.partner._create_sponsor_campaign()

        self.assertEqual(self.partner.sponsor_campaign_id, campaign)
        self.assertEqual(
            self.env["coupon.campaign"].search(
                [("sponsor_partner_ids", "=", self.partner.id)]
            ),
            campaign,
        )

    def test_sponsor_campaign_creation_upon_contract_start(self):
        "Starting a contract should trigger the creation of a sponsorship campaign"
        self.assertFalse(self.partner.sponsor_campaign_id)

        contract = self.create_contract(self.partner)
        contract.write({"date_start": "2026-01-01"})

        self.assertTrue(self.partner.sponsor_campaign_id)

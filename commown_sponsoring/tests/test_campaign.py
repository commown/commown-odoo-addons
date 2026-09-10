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

    def test_sponsor_code_unique_among_single_company(self):
        "B2B sustomers should only have one sponsor campaign among their company."
        company = self.env.ref("base.res_partner_1")
        empl1 = self.env["res.partner"].create(
            {"name": "Employee 1", "email": "e1@test.coop", "parent_id": company.id}
        )

        self.assertFalse((empl1 | company).sponsor_campaign_id)

        empl1._create_sponsor_campaign()
        campaign = empl1.commercial_partner_id.sponsor_campaign_id
        self.assertTrue(campaign)
        self.assertEqual(campaign, company.sponsor_campaign_id)

        # Newcomers to the company should have access to the sponsor campaign
        empl2 = self.env["res.partner"].create(
            {"name": "Employee 2", "email": "e2@test.coop", "parent_id": company.id}
        )
        self.assertEqual(campaign, empl2.commercial_partner_id.sponsor_campaign_id)

    def test_sponsor_campaign_creation_upon_contract_start(self):
        "Starting a contract should trigger the creation of a sponsorship campaign"
        self.assertFalse(self.partner.sponsor_campaign_id)

        contract = self.create_contract(self.partner)
        contract.write({"date_start": "2026-01-01"})

        self.assertTrue(self.partner.sponsor_campaign_id)

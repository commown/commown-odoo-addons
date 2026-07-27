from datetime import date, timedelta
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import Form, TransactionCase

from odoo.addons.commown_shipping.models.delivery_mixin import ParcelError
from odoo.addons.queue_job.tests.common import trap_jobs

from ..models.delivery_mixin import CommownTrackDeliveryMixin as DeliveryMixin


def _mock_delivery_job(job, result):
    with patch.object(
        DeliveryMixin,
        "_delivery_tracking_colissimo_status",
        side_effect=result,
    ):
        job.perform()


class CheckMailMixin:
    "Small helper class to check sent emails easily"

    def _check_mail(self, mail, subject, content, check_recipients=None):
        self.assertEqual(mail.message_type, "notification")
        self.assertEqual(mail.subject, subject)
        self.assertIn(content, mail.body)
        if check_recipients is not None:
            self.assertItemsEqual(mail.partner_ids.mapped("name"), check_recipients)
        return mail

    def _object_messages(self, obj):
        return self.env["mail.message"].search(
            [("res_id", "=", obj.id), ("model", "=", obj._name)]
        )


class CrmLeadDeliveryTC(TransactionCase, CheckMailMixin):
    def setUp(self):
        super().setUp()
        team = self.env.ref("sales_team.salesteam_website_sales")
        team.update(
            {
                "delivery_tracking": True,
                "on_delivery_email_template_id": self.env.ref(
                    "commown_shipping.delivery_email_example"
                ).id,
            }
        )
        self.lead = (
            self.env["crm.lead"]
            .with_context(test_commown_shipping_no_contract_check=True)
            .create(
                {
                    "name": "[SO99999-01] TEST DELIVERY",
                    "partner_id": self.env.ref("base.res_partner_1").id,
                    "type": "opportunity",
                    "team_id": team.id,
                }
            )
        )

    def check_mail_delivered(self, subject, code):
        last_message = self._object_messages(self.lead)[0]
        return self._check_mail(last_message, subject, "code: " + code)

    def test_delivery_email_template(self):
        # Shipping deactivated, template set => None expected
        self.lead.team_id.delivery_tracking = False
        assert (
            self.lead.team_id.on_delivery_email_template_id
        ), "test prerequisite error"
        self.assertIsNone(self.lead.delivery_email_template())

        # Shipping activated, no lead custom template => custom expected
        self.lead.team_id.delivery_tracking = True
        self.lead.on_delivery_email_template_id = False
        self.assertEqual(
            self.lead.delivery_email_template(),
            self.lead.team_id.on_delivery_email_template_id,
        )

        # Shipping activated, custom template => custom expected
        self.lead.on_delivery_email_template_id = (
            self.lead.team_id.on_delivery_email_template_id.copy().id
        )
        self.assertEqual(
            self.lead.delivery_email_template().name, "Post-delivery email (copy)"
        )

        # Shipping deactivated, even with custom template => None expected
        self.lead.team_id.delivery_tracking = False
        self.assertIsNone(self.lead.delivery_email_template())

    def test_default_send_email_on_delivery_without_ui(self):
        """
        The default value of send_email_on_delivery should match
        the lead's team default_perform_actions_on_delivery value,
        both from the record itself, and from the context value default_team_id.
        (Using the create method without UI)
        """
        # Setup
        team = self.lead.team_id
        lead_model = self.env["crm.lead"].with_context(
            test_commown_shipping_no_contract_check=True
        )

        # Case 1: actions are enabled by default
        team.default_perform_actions_on_delivery = True
        lead_w_actions = lead_model.create({"name": "Lead 1", "team_id": team.id})

        self.assertTrue(lead_w_actions.send_email_on_delivery)

        # Case 2: actions are enabled by default
        team.default_perform_actions_on_delivery = False
        lead_w_out_actions = lead_model.create({"name": "Lead 1", "team_id": team.id})

        self.assertFalse(lead_w_out_actions.send_email_on_delivery)

    def test_default_send_email_on_delivery_with_ui(self):
        "Same as previous code, but using the web UI with the context"
        team = self.lead.team_id

        def assertFormSendEmailOnDelivery():
            form = Form(
                self.env["crm.lead"].with_context(
                    default_team_id=team.id,
                    test_commown_shipping_no_contract_check=True,
                )
            )
            self.assertEqual(
                form.send_email_on_delivery, team.default_perform_actions_on_delivery
            )

            form.name = "Dummy name"
            lead = form.save()
            self.assertEqual(
                lead.send_email_on_delivery, team.default_perform_actions_on_delivery
            )

        # Case 1: actions are enabled by default
        team.default_perform_actions_on_delivery = True
        assertFormSendEmailOnDelivery()

        # Case 2: actions are disabled by default
        team.default_perform_actions_on_delivery = False
        assertFormSendEmailOnDelivery()

    def test_actions_on_delivery_send_email_team_template(self):
        self.assertTrue(self.lead.send_email_on_delivery)

        # Simulate delivery
        self.lead.expedition_status = "[LIVCFM] Test"
        self.lead.delivery_date = date(2018, 1, 1)

        # Check result
        self.check_mail_delivered("Product delivered", "LIVCFM")

    def test_actions_on_delivery_send_email_no_status(self):
        "Check empty expedition status is OK"

        self.assertTrue(self.lead.send_email_on_delivery)

        # Simulate delivery
        self.lead.expedition_status = False
        self.lead.delivery_date = "2018-01-01"

        # Check result
        self.check_mail_delivered("Product delivered", "EMPTY_CODE")

    def test_actions_on_delivery_send_email_custom_template(self):
        self.assertTrue(self.lead.send_email_on_delivery)

        self.lead.on_delivery_email_template_id = (
            self.lead.team_id.on_delivery_email_template_id.copy(  # noqa: B950
                {"subject": "Test custom email"}
            ).id
        )

        # Simulate delivery
        self.lead.expedition_status = "[LIVGAR] Test"
        self.lead.delivery_date = "2018-01-01"

        # Check result
        self.check_mail_delivered("Test custom email", "LIVGAR")

    def test_actions_on_delivery_send_email_no_template(self):
        "A user error must be raised in the case no template was specified"

        self.assertTrue(self.lead.send_email_on_delivery)

        self.lead.on_delivery_email_template_id = False
        self.lead.team_id.on_delivery_email_template_id = False

        # Simulate delivery
        self.assertRaises(UserError, self.lead.update, {"delivery_date": "2018-01-01"})


def _status(code, label="test label", _date=None):
    return {"code": code, "label": label, "date": _date or date.today().isoformat()}


class CrmLeadDeliveryTrackingTC(TransactionCase, CheckMailMixin):
    def setUp(self):
        super().setUp()

        account = self.env.ref("commown_shipping.carrier-account-colissimo-std-account")
        self.team = self.env.ref("sales_team.salesteam_website_sales")
        mt_id = self.env.ref("commown_shipping.delivery_email_example").id
        self.team.update(
            {
                "delivery_tracking": True,
                "carrier_account_id": account.id,
                "default_perform_actions_on_delivery": False,
                "on_delivery_email_template_id": mt_id,
            }
        )
        self.stage_track = self._add_stage("Wait [colissimo: tracking]", self.team)
        self.lead1 = self._add_lead("l1", self.stage_track, self.team, "ref1")
        self.lead2 = self._add_lead("l2", self.stage_track, self.team, "ref2")
        self.lead3 = self._add_lead("l3", self.stage_track, self.team, "https://c.coop")
        self.stage_final = self._add_stage("OK [colissimo: final]", self.team)
        self.lead4 = self._add_lead("l4", self.stage_final, self.team, "ref4")

    def _add_stage(self, name, team, **kwargs):
        kwargs.update({"name": name, "team_id": team.id})
        return self.env["crm.stage"].create(kwargs)

    def _add_lead(self, name, stage, team, ref, **kwargs):
        kwargs.update(
            {
                "name": name,
                "stage_id": stage.id,
                "team_id": team.id,
                "expedition_ref": ref,
            }
        )
        # Imitate context passed by web UI
        lead_model = self.env["crm.lead"].with_context(
            default_team_id=team.id, test_commown_shipping_no_contract_check=True
        )
        return lead_model.create(kwargs)

    def test_tracked_records(self):
        team2 = self.stage_track.team_id.copy(
            {"name": "Test team", "delivery_tracking": False}
        )
        stage_track2 = self._add_stage("Wait2 [colissimo: tracking]", team2)
        self._add_lead("l21", stage_track2, team2, "l21ref")
        self._add_stage("Done2 [colissimo: final]", team2)

        self.assertEqual(
            self.env["crm.lead"]._delivery_tracked_records().ids,
            [self.lead2.id, self.lead1.id],
        )

    def exec_job_with_status(self, lead_statuses):
        """Run the delivery jobs mocking colissimo WS with given status
        Return the leads in the order of their name in `lead_statuses`.
        """
        with trap_jobs() as trap:
            leads = self.env["crm.lead"]._cron_delivery_auto_track()

        trap.assert_jobs_count(len(lead_statuses))

        for job in trap.enqueued_jobs:
            _mock_delivery_job(job, lambda *args: lead_statuses[job.recordset.name])

        return leads.sorted(lambda l: list(lead_statuses.keys()).index(l.name))

    def test_cron_ok1(self):
        leads = self.exec_job_with_status(
            {lead: _status("LIVCFM") for lead in ("l1", "l2")}
        )

        self.assertEqual(leads.mapped("expedition_status"), ["[LIVCFM] test label"] * 2)
        self.assertEqual(leads.mapped("stage_id"), self.stage_final)

    def test_duplicated_tracking_job(self):
        "Re-submitted jobs before the first ones were completed must do nothing"

        def _delivered_parcel_emails(lead):
            return self._object_messages(lead).filtered(
                lambda m: m.subject == "Product delivered"
            )

        # Simulate jobs are re-created (trap2) before the others are ended (trap1):
        with trap_jobs() as trap1:
            leads1 = self.env["crm.lead"]._cron_delivery_auto_track()

        with trap_jobs() as trap2:
            leads2 = self.env["crm.lead"]._cron_delivery_auto_track()

        # Check the concerned leads are the same
        self.assertTrue(len(leads1) > 0 and leads1 == leads2)

        tracking_results = {l: _status("LIVCFM") for l in ("l1", "l2")}

        for job in trap1.enqueued_jobs:
            lead = job.recordset
            lead.send_email_on_delivery = True
            _mock_delivery_job(job, lambda *args: tracking_results[lead.name])
            self.assertEqual(len(_delivered_parcel_emails(lead)), 1)

        # Execute duplicated jobs and check their result: job skipped, email not sent
        for job in trap2.enqueued_jobs:
            job.perform()  # No need to mock here as we return before calling colissimo
            self.assertIn("Skipping", job.result)
            lead = job.recordset
            self.assertEqual(len(_delivered_parcel_emails(lead)), 1)

    def test_cron_ok2(self):
        lead1, lead2 = self.exec_job_with_status(
            {"l1": _status("LIVCFM"), "l2": _status("RENLNA")}
        )

        self.assertItemsEqual(lead1.expedition_status, "[LIVCFM] test label")
        self.assertItemsEqual(lead2.expedition_status, "[RENLNA] test label")

        self.assertItemsEqual(lead1.stage_id, self.stage_final)
        self.assertItemsEqual(lead2.stage_id, self.stage_track)

    def test_cron_ok_mlvars1(self):
        self.env["crm.lead"]._cron_delivery_auto_track()
        lead1, lead2 = self.exec_job_with_status(
            {"l1": _status("LIVCFM"), "l2": _status("MLVARS")}
        )

        self.assertEqual(lead1.expedition_status, "[LIVCFM] test label")
        self.assertEqual(lead2.expedition_status, "[MLVARS] test label")

        self.assertEqual(lead1.stage_id, self.stage_final)
        self.assertEqual(lead2.stage_id, self.stage_track)

        self.assertFalse(lead1.expedition_urgency_mail_sent)
        self.assertFalse(lead2.expedition_urgency_mail_sent)

        self.assertEqual(
            lead1.mapped("message_ids.subtype_id.name"),
            ["Opportunity Created"],
        )

        self.assertEqual(
            lead2.mapped("message_ids.subtype_id.name"),
            ["Opportunity Created"],
        )

    def test_cron_ok_mlvars2(self):
        lead1, lead2 = self.lead1, self.lead2

        partner_id = self.env.ref("base.res_partner_1").id
        lead2.partner_id = partner_id
        lead2.message_follower_ids |= self.env["mail.followers"].create(
            {"partner_id": partner_id, "res_model": lead2._name, "res_id": lead2.id},
        )
        lead2.send_email_on_delivery = True

        date_old = (date.today() - timedelta(days=9)).isoformat()
        self.exec_job_with_status(
            {"l1": _status("LIVCFM"), "l2": _status("MLVARS", _date=date_old)},
        )

        self.assertEqual(lead1.expedition_status, "[LIVCFM] test label")
        self.assertEqual(lead2.expedition_status, "[MLVARS] test label")

        self.assertEqual(lead1.stage_id, self.stage_final)
        self.assertEqual(lead2.stage_id, self.stage_track)

        self.assertFalse(lead1.expedition_urgency_mail_sent)
        self.assertTrue(lead2.expedition_urgency_mail_sent)

        self.assertEqual(
            lead1.mapped("message_ids.subtype_id.name"),
            ["Opportunity Created"],
        )

        self.assertEqual(
            lead2.mapped("message_ids.subtype_id.name"),
            ["Note", "Discussions", "Opportunity Created"],
        )

        msg1, msg2 = lead2.message_ids[:2]
        subject = (
            "%s - Customer parcel waiting at the postoffice" % lead2.company_id.name
        )
        self._check_mail(msg1, subject, "postoffice", [lead2.company_id.name])
        self._check_mail(msg2, "Product delivered", "code: MLVARS", ["Wood Corner"])

    @patch(
        "odoo.addons.commown_shipping.models.delivery_mixin.colissimo_status_request",
    )
    def test_delivery_tracking_colissimo_status(self, mock_collisimo_status):
        code = "1"
        label = "label"
        date = "2023-01-01"

        mock_collisimo_status.return_value = (
            "<doc>"
            "  <eventCode>%(code)s</eventCode>"
            "  <eventDate>%(date)s</eventDate>"
            "  <eventLibelle>%(label)s</eventLibelle>"
            "</doc>"
            % {
                "code": code,
                "label": label,
                "date": date,
            }
        )

        self.assertEqual(
            self.lead1._delivery_tracking_colissimo_status(),
            {"code": code, "label": label, "date": date},
        )

        bad_resp = "<doc></doc>"
        mock_collisimo_status.return_value = bad_resp
        expected_msg = "Error requesting parcel status for %s. Response was:\n%s" % (
            self.lead1,
            bad_resp,
        )
        with self.assertRaises(ParcelError) as err:
            self.lead1._delivery_tracking_colissimo_status()
        self.assertEqual(err.exception.args[0], expected_msg)

from datetime import date, timedelta

import requests
from mock import patch
from odoo.addons.commown_shipping.models.colissimo_utils import shipping_data
from odoo.addons.commown_shipping.models.delivery_mixin import \
    CommownTrackDeliveryMixin as DeliveryMixin
from odoo.addons.queue_job.job import Job
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, at_install, post_install

from .common import BaseShippingTC, pdf_page_num


@at_install(False)
@post_install(True)
class CrmLeadShippingTC(BaseShippingTC):
    def setUp(self):
        super(CrmLeadShippingTC, self).setUp()

        partner = self.env.ref("base.res_partner_1")
        product = self.env["product.product"].create(
            {"name": "Fairphone", "shipping_parcel_type_id": self.parcel_type.id}
        )
        team = self.env.ref("sales_team.salesteam_website_sales")
        team.shipping_account_id = self.shipping_account

        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom": product.uom_id.id,
                            "name": product.name,
                            "product_uom_qty": 1,
                            "price_unit": product.list_price,
                        },
                    )
                ],
            }
        )

        self.lead = self.env["crm.lead"].create(
            {
                "name": "[SO00000] Fake order",
                "partner_id": partner.id,
                "type": "opportunity",
                "team_id": team.id,
                "so_line_id": so.order_line[0].id,
            }
        )

    def _country(self, code):
        return self.env["res.country"].search([("code", "=", code)])

    def test_shipping_data_product_code(self):
        base_kwargs = {
            "sender": self.env["res.partner"],
            "recipient": self.lead.partner_id,
            "order_number": "SO00000",
            "commercial_name": "Commown",
            "weight": 0.5,
        }

        # French label
        self.lead.partner_id.country_id = self._country("FR")
        data = shipping_data(**base_kwargs)
        self.assertEqual(data["letter"]["service"]["productCode"], "DOS")

        # French return label
        data = shipping_data(is_return=True, **base_kwargs)
        self.assertEqual(data["letter"]["service"]["productCode"], "CORE")

        # International label
        self.lead.partner_id.country_id = self._country("BE")
        data = shipping_data(**base_kwargs)
        self.assertEqual(data["letter"]["service"]["productCode"], "COLI")

        # International Return label
        self.lead.partner_id.country_id = self._country("BE")
        data = shipping_data(is_return=True, **base_kwargs)
        self.assertEqual(data["letter"]["service"]["productCode"], "CORI")

    def _print_outward_labels(self, leads):
        act = self.env.ref("commown_shipping.action_print_outward_label_lead")

        with patch.object(requests, "post", return_value=self.fake_resp):
            return act.with_context(
                {"active_model": leads._name, "active_ids": leads.ids}
            ).run()

    def test_shipping_data_address_too_long(self):
        """ When a partner has a too long address, a user error is raised
        with its name (useful when printing several labels at once).
        """
        other_partner = self.lead.partner_id.copy({"street": "x" * 100})
        other_partner.name = "John TestAddressTooLong"

        leads = self.env["crm.lead"]
        for num in range(5):
            leads += self.lead.copy({"name": "[SO%05d] Test lead" % num})
            if num == 3:
                leads[-1].partner_id = other_partner

        with self.assertRaises(UserError) as err:
            self._print_outward_labels(leads)
        self.assertEqual(
            err.exception.name, 'Address too long for "John TestAddressTooLong"'
        )

    def test_shipping_data_empty_name(self):
        self.lead.partner_id.firstname = False
        data = shipping_data(
            sender=self.env["res.partner"],
            recipient=self.lead.partner_id,
            order_number="SO00000",
            commercial_name="Commown",
            weight=0.5,
        )
        self.assertEqual(data["letter"]["addressee"]["address"]["firstName"], "")

    def test_create_parcel_label(self):
        lead = self.lead

        with patch.object(requests, "post", return_value=self.fake_resp):
            lead._create_parcel_label(
                self.parcel_type,
                self.shipping_account,
                lead.partner_id,
                lead.get_label_ref(),
            )

        self.assertEqual(lead.expedition_ref, "6X0000000000")
        self.assertEqual(lead.expedition_date, date.today())
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", "crm.lead"), ("res_id", "=", lead.id)]
        )
        self.assertEqual(len(attachments), 1)
        att = attachments[0]
        self.assertEqual(att.datas_fname, "6X0000000000.pdf")
        self.assertEqual(att.name, self.parcel_type.name + ".pdf")
        self.assertEqualFakeLabel(att)

    def test_print_parcel_action(self):
        leads = self.env["crm.lead"]
        for num in range(5):
            leads += self.lead.copy({"name": "[SO%05d] Test lead" % num})

        download_action = self._print_outward_labels(leads)

        all_labels = self._attachment_from_download_action(download_action)
        self.assertEqual(all_labels.name, self.parcel_type.name + ".pdf")
        self.assertEqual(pdf_page_num(all_labels), 2)


@at_install(False)
@post_install(True)
class CrmLeadDeliveryTC(TransactionCase):
    def setUp(self):
        super(CrmLeadDeliveryTC, self).setUp()
        team = self.env.ref("sales_team.salesteam_website_sales")
        team.update(
            {
                "delivery_tracking": True,
                "on_delivery_email_template_id": self.env.ref(
                    "commown_shipping.delivery_email_example"
                ).id,
            }
        )
        self.lead = self.env["crm.lead"].create(
            {
                "name": "[SO99999-01] TEST DELIVERY",
                "partner_id": self.env.ref("base.res_partner_1").id,
                "type": "opportunity",
                "team_id": team.id,
            }
        )

    def _last_message(self):
        return self.env["mail.message"].search(
            [("res_id", "=", self.lead.id), ("model", "=", "crm.lead")]
        )[0]

    def check_mail_delivered(self, subject, code):
        last_message = self._last_message()
        self.assertEqual(last_message.message_type, "notification")
        self.assertEqual(last_message.subject, subject)
        self.assertIn("code: %s" % code, last_message.body)
        return last_message

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

    def test_actions_on_delivery_send_email_team_template(self):

        self.assertTrue(self.lead.send_email_on_delivery)

        # Simulate delivery
        self.lead.expedition_status = "[LIVCFM] Test"
        self.lead.delivery_date = date(2018, 1, 1)

        # Check result
        self.check_mail_delivered("Product delivered", "LIVCFM")

    def test_actions_on_delivery_send_email_no_status(self):
        " Check empty expedition status is OK "

        self.assertTrue(self.lead.send_email_on_delivery)

        # Simulate delivery
        self.lead.expedition_status = False
        self.lead.delivery_date = "2018-01-01"

        # Check result
        self.check_mail_delivered("Product delivered", "EMPTY_CODE")

    def test_actions_on_delivery_send_email_custom_template(self):

        self.assertTrue(self.lead.send_email_on_delivery)

        self.lead.on_delivery_email_template_id = self.lead.team_id.on_delivery_email_template_id.copy(  # noqa: B950
            {"subject": "Test custom email"}
        ).id

        # Simulate delivery
        self.lead.expedition_status = "[LIVGAR] Test"
        self.lead.delivery_date = "2018-01-01"

        # Check result
        self.check_mail_delivered("Test custom email", "LIVGAR")

    def test_actions_on_delivery_send_email_no_template(self):
        " A user error must be raised in the case no template was specified "

        self.assertTrue(self.lead.send_email_on_delivery)
        self.lead.on_delivery_email_template_id = False
        self.lead.team_id.on_delivery_email_template_id = False

        # Simulate delivery
        self.assertRaises(UserError, self.lead.update, {"delivery_date": "2018-01-01"})


def _status(code, label="test label", _date=None):
    return {"code": code, "label": label, "date": _date or date.today().isoformat()}


@at_install(False)
@post_install(True)
class CrmLeadDeliveryTrackingTC(TransactionCase):
    def setUp(self):
        super(CrmLeadDeliveryTrackingTC, self).setUp()

        account = self.env.ref(
            "commown_shipping.shipping-account-colissimo-std-account")
        self.team = self.env.ref("sales_team.salesteam_website_sales")
        mt_id = self.env.ref("commown_shipping.delivery_email_example").id
        self.team.update(
            {
                "delivery_tracking": True,
                "shipping_account_id": account.id,
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
        return self.env["crm.lead"].create(kwargs)

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

    def _perform_jobs_with_colissimo_status(self, *statuses):
        queued_jobs = self.env["queue.job"].search([])
        if len(statuses) == 1:
            statuses = [statuses[0]] * len(queued_jobs)

        self.assertEqual(queued_jobs.mapped("state"), ["pending"] * len(statuses))

        for status, queued_job in zip(statuses, queued_jobs):
            job = Job.load(self.env, queued_job.uuid)
            with patch.object(
                DeliveryMixin,
                "_delivery_tracking_colissimo_status",
                side_effect=lambda *args: status,
            ):
                job.perform()

    def test_cron_ok1(self):
        leads = self.env["crm.lead"]._cron_delivery_auto_track()
        self._perform_jobs_with_colissimo_status(_status("LIVCFM"))

        self.assertEqual(leads.mapped("expedition_status"), ["[LIVCFM] test label"] * 2)
        self.assertEqual(leads.mapped("stage_id"), self.stage_final)

    def test_cron_ok2(self):
        leads = self.env["crm.lead"]._cron_delivery_auto_track()
        self._perform_jobs_with_colissimo_status(_status("LIVCFM"), _status("RENLNA"))

        self.assertItemsEqual(
            leads.mapped("expedition_status"),
            ["[LIVCFM] test label", "[RENLNA] test label"],
        )
        self.assertItemsEqual(
            leads.mapped("stage_id"), [self.stage_final, self.stage_track]
        )

    def test_cron_ok_mlvars1(self):
        leads = self.env["crm.lead"]._cron_delivery_auto_track()
        self._perform_jobs_with_colissimo_status(_status("LIVCFM"), _status("MLVARS"))

        self.assertItemsEqual(
            leads.mapped("expedition_status"),
            ["[LIVCFM] test label", "[MLVARS] test label"],
        )
        self.assertItemsEqual(
            leads.mapped("stage_id"), [self.stage_final, self.stage_track]
        )
        self.assertEqual(leads.mapped("expedition_urgency_mail_sent"), [False, False])
        self.assertEqual(
            leads.mapped("message_ids.subtype_id.name"), ["Opportunity Created"]
        )

    def test_cron_ok_mlvars2(self):
        leads = self.env["crm.lead"]._cron_delivery_auto_track()
        date_old = (date.today() - timedelta(days=9)).isoformat()
        self._perform_jobs_with_colissimo_status(
            _status("LIVCFM"), _status("MLVARS", _date=date_old)
        )

        self.assertItemsEqual(
            leads.mapped("expedition_status"),
            ["[LIVCFM] test label", "[MLVARS] test label"],
        )
        self.assertItemsEqual(
            leads.mapped("stage_id"), [self.stage_final, self.stage_track]
        )
        self.assertItemsEqual(
            leads.mapped("expedition_urgency_mail_sent"), [True, False]
        )
        self.assertItemsEqual(
            leads.mapped("message_ids.subtype_id.name"),
            ["Opportunity Created", "Discussions"],
        )

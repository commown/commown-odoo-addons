from contextlib import contextmanager

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone
from odoo.addons.queue_job.tests.common import trap_jobs


class NoSMSAssertMixin:
    @contextmanager
    def assertNoSMSLogged(self):
        chan = "odoo.addons.commown_support.models.project_task"
        with self.assertLogs(chan, level="WARNING") as logged:
            yield
        self.assertEqual(len(logged.output), 1)
        self.assertIn("No SMS reminder sent", logged.output[0])


@tagged("-at_install", "post_install")
class ProjectTaskModelTC(NoSMSAssertMixin, TransactionCase):
    def test_followup_view(self):
        project = self.env.ref("commown_support.support_project")
        project.show_internal_followup = True

        partner = self.env.ref("base.partner_demo_portal")
        task = self.env["project.task"].create(
            {
                "name": "Commown test",
                "project_id": project.id,
                "partner_id": partner.id,
                "internal_followup": "<p>Coucou</p>",
            }
        )
        self.env["mail.followers"].create(
            {
                "partner_id": partner.id,
                "res_id": task.id,
                "res_model": "project.task",
            }
        )

        demo_user = self.env.ref("base.user_demo")
        task_user = self.env["project.task"].with_user(demo_user).browse(task.id)
        self.assertEqual(task_user.name, "Commown test")
        self.assertEqual(task_user.internal_followup, "<p>Coucou</p>")

        task_portal = (
            self.env["project.task"].with_user(partner.user_ids).browse(task.id)
        )
        self.assertEqual(task_portal.name, "Commown test")
        with self.assertRaises(AccessError) as err:
            task_portal.internal_followup  # pylint: disable=pointless-statement
        self.assertIn("not have enough rights to access", err.exception.args[0])
        self.assertIn("internal_followup", err.exception.args[0])


@tagged("-at_install", "post_install")
class ProjectTaskActionTC(NoSMSAssertMixin, TransactionCase):
    def flush_tracking(self):
        """Force the creation of tracking values."""
        self.env.flush_all()
        self.cr.precommit.run()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project = cls.env.ref("commown_support.support_project")

        # Adapt defined stages to our needs: use expected name
        # conventions and remove email model as they are buggy for
        # issues (their template model is task instead, which leads to
        # crashes)
        cls.stage_pending = cls.env["project.task.type"].create(
            {"name": "Working on it [after-sale: pending]", "mail_template_id": False}
        )
        cls.stage_pending.project_ids |= cls.project

        cls.stage_reminder = cls.stage_pending.copy(
            {
                "name": "Remind email [after-sale: reminder-email]",
                "mail_template_id": False,
            }
        )

        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.partner.update({"firstname": "Flo", "phone": "+33747397654"})

        cls.task = cls.env["project.task"].create(
            {
                "name": "Commown test",
                "project_id": cls.project.id,
                "stage_id": cls.stage_pending.id,
                "partner_id": cls.partner.id,
                "user_ids": cls.env.ref("base.user_demo").ids,
            }
        )

    def assertIsReminderEmail(self, message):
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_comment"))
        self.assertEqual(
            message.subject, "Commown : votre demande d'assistance se languit de vous !"
        )
        self.assertEqual(message.author_id, self.env.ref("base.user_demo").partner_id)

    def assertIsStageChangeMessage(self, message):
        self.assertEqual(message.subtype_id, self.env.ref("project.mt_task_stage"))

    def test_send_reminders(self):
        """A reminder mail to followers and SMS to partner must be sent
        when task is put in the dedicated column.
        """

        message_num = len(self.task.message_ids)
        fr = self.env.ref("base.fr")
        self.task.partner_id.update({"country_id": fr.id, "phone": "+33747397654"})
        with trap_jobs() as trap:
            self.flush_tracking()  # Making sure a tracking discard will not impact next flush

            self.task.update({"stage_id": self.stage_reminder.id})
            self.flush_tracking()
        trap.assert_jobs_count(1, only=self.task._message_sms_with_template)

        # Check email message
        # 2 expected messages: email, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 2)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        self.assertIsReminderEmail(self.task.message_ids[1])

        # Check job for sms has been posted
        country_code = self.task.partner_id.country_id.code
        partner_mobile = normalize_phone(
            self.task.partner_id.get_mobile_phone(),
            country_code,
        )

        trap.perform_enqueued_jobs()

        # Check whether a SMS text was created, with the partner mobile as number
        task_sms = self.task.message_ids.filtered(lambda m: m.message_type == "sms")
        self.assertTrue(task_sms)
        self.assertEqual(task_sms.notification_ids.sms_number, partner_mobile)

    def test_send_reminder_no_sms(self):
        """A reminder SMS must not be sent when a non-employee message
        (interpreted as a message from the partner) has already been sent.
        """

        # Check test prerequisite: task's partner is not an employee
        assert self.env.ref("base.group_user") not in self.task.partner_id.mapped(
            "user_ids.groups_id"
        )

        # Simulate partner sending a message, then put task back to reminder
        self._send_partner_email()
        message_num = len(self.task.message_ids)
        with self.assertNoSMSLogged():
            self.flush_tracking()  # Making sure a tracking discard will not impact next flush

            self.task.update({"stage_id": self.stage_reminder.id})
            self.flush_tracking()

        # 2 expected messages: email, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 2)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        self.assertIsReminderEmail(self.task.message_ids[1])

    def _send_partner_email(self, task=None, author_id=None):
        if task is None:  # pragma: no cover
            task = self.task
        self.env["mail.message"].create(
            {
                "author_id": author_id or task.partner_id.id,
                "subject": "Test subject",
                "body": "<p>Test body</p>",
                "message_type": "comment",
                "model": "project.task",
                "res_id": task.id,
                "subtype_id": self.env.ref("mail.mt_comment").id,
            }
        )

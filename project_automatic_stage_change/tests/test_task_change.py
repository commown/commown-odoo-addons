import datetime

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


def now_plus_days_timedelta(_days):
    return datetime.datetime.now() + datetime.timedelta(days=_days)


class CommonAutomaticStageChangeTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project = cls.env["project.project"].create({"name": "Test Project"})

        # Test stages
        cls.stage_default = cls.env["project.task.type"].create(
            {"name": "Default stage", "project_ids": [Command.set(cls.project.ids)]}
        )

        cls.stage_5_days = cls.stage_default.copy(
            {
                "name": "Five-days wait",
                "has_timely_stage_change": True,
                "timely_stage_change_days": 5,
                "timely_stage_dest": cls.stage_default.id,
            }
        )

        cls.stage_10_days = cls.stage_default.copy(
            {
                "name": "Ten-days wait",
                "has_timely_stage_change": True,
                "timely_stage_change_days": 10,
                "timely_stage_dest": cls.stage_5_days.id,
            }
        )

        # Test tasks
        cls.task = cls.env["project.task"].create(
            {
                "name": "Test Task 1",
                "project_id": cls.project.id,
                "stage_id": cls.stage_default.id,
            }
        )


class PassiveAutomaticStageChangeTC(CommonAutomaticStageChangeTC):
    def _set_task_stage_with_form(self, task, dest_stage):
        with Form(task) as task_edit:
            task_edit.stage_id = dest_stage

    def test_change_datetime_on_tasks(self):
        "The change time field should be applied upon setting a stage manually"
        self.assertFalse(self.task.timely_stage_change_datetime)

        self._set_task_stage_with_form(self.task, self.stage_5_days)
        self.assertEqual(
            self.task.timely_stage_change_datetime.date(),
            now_plus_days_timedelta(5).date(),
        )

        self._set_task_stage_with_form(self.task, self.stage_10_days)
        self.assertEqual(
            self.task.timely_stage_change_datetime.date(),
            now_plus_days_timedelta(10).date(),
        )

        self._set_task_stage_with_form(self.task, self.stage_default)
        self.assertFalse(self.task.timely_stage_change_datetime)

    def _reset_and_check_actions(self):
        self.env.ref(
            "project_automatic_stage_change.passive_stage_change_automation"
        ).last_run = False
        self.env["base.automation"]._check()

    def test_passive_change_upon_passed_date(self):
        "Tasks should move around based on their timely stage change datetime"
        self.task.stage_id = self.stage_5_days
        self.task.timely_stage_change_datetime = now_plus_days_timedelta(-1)

        self._reset_and_check_actions()

        self.assertEqual(self.task.stage_id, self.stage_default)


@tagged("-at_install", "post_install")
class ActiveAutomaticStageChangeTC(CommonAutomaticStageChangeTC):
    def test_active_change_upon_message_receiving(self):
        "When a destination stage for message reception is set, the task should be moved accordingly"
        portal_partner = self.env.ref("base.partner_demo_portal")

        def _send_message_from_portal_partner(task):
            task.message_post(
                body="Dummy text",
                author_id=portal_partner.id,
                message_type="email",
                subtype_xmlid="mail.mt_comment",
            )

        # Case 1: no destination stage is set
        stage_before_moving = self.task.stage_id

        self.project.dest_stage_on_customer_message = False
        _send_message_from_portal_partner(self.task)

        self.assertEqual(self.task.stage_id, stage_before_moving)

        # Case 2: Moving to a stage with a set timely date
        self.project.dest_stage_on_customer_message = self.stage_5_days

        _send_message_from_portal_partner(self.task)
        self.task.invalidate_recordset()

        self.assertEqual(self.task.stage_id, self.stage_5_days)

    def test_no_active_change_with_internal_user(self):
        "The task should not move upon receiving a message from an internal user"
        self.project.dest_stage_on_customer_message = self.stage_5_days

        stage_before_moving = self.task.stage_id
        self.assertNotEqual(stage_before_moving, self.stage_5_days)

        self.task.message_post(
            body="Dummy text",
            author_id=self.env.ref("base.partner_demo").id,
            message_type="email",
            subtype_xmlid="mail.mt_comment",
        )

        self.assertEqual(self.task.stage_id, stage_before_moving)

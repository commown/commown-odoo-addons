from odoo.tests import TransactionCase


class CommownBaseAutomationTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model_id = cls.env.ref("project.model_project_task").id

        cls.auto = cls.env["base.automation"].create(
            {"name": "Test automation", "model_id": model_id, "trigger": "on_create"}
        )

        cls.control = cls.env["commown_automated_control.automated_control"].create(
            {
                "name": "Test Control",
                "model_id": model_id,
                "filter_domain": "[(project_id, =, 0)]",
                "user_message": "Test Control",
            }
        )

    def test_compute_automated_control_id(self):
        # Case 1: No automated control record is assigned to the automation
        self.assertFalse(self.auto.automated_control_id)

        # Case 2: At least one automated control record is assigned to the automation
        self.auto.automated_control_ids = self.control
        self.assertEqual(self.auto.automated_control_id, self.control)

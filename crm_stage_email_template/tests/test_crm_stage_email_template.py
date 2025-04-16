from odoo.tests import TransactionCase


class TestCrmStageEmailTemplate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Template
        cls.test_template = cls.env["mail.template"].create(
            {
                "name": "Test template",
            }
        )

        # Lead
        cls.test_lead = cls.env["crm.lead"].create(
            {
                "name": "Test lead",
                "type": "lead",
            }
        )

    def test_crm_stage_w_template_id(self):
        # Templates when stage_id is False (= No stage)
        self.assertEqual({}, self.test_lead._track_template(["stage_id"]))

        stage_w_template = self.env["crm.stage"].create(
            {
                "name": "Stage with template",
                "mail_template_id": self.test_template.id,
            }
        )

        self.test_lead.stage_id = stage_w_template.id

        # Templates when no stage_id changes
        self.assertEqual({}, self.test_lead._track_template(["type"]))

        # Templates when stage_id changes
        templates_stage_change = self.test_lead._track_template(["stage_id"])
        self.assertIn("stage_id", templates_stage_change.keys())
        self.assertEqual(self.test_template, templates_stage_change["stage_id"][0])

    def test_crm_stage_w_out_template_id(self):
        stage_w_out_template = self.env["crm.stage"].create(
            {
                "name": "Stage without template",
            }
        )
        self.assertFalse(stage_w_out_template.mail_template_id)

        self.test_lead.stage_id = stage_w_out_template.id

        # Templates when stage_id.mail_template_id is False
        self.assertEqual({}, self.test_lead._track_template(["stage_id"]))

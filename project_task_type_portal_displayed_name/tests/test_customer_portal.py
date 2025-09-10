from odoo.tests import HttpCase


class ProjectTaskTypePortalDisplayedNameTC(HttpCase):
    def test_task_type_portal_displayed_name(self):
        # Setup
        self.authenticate("portal", "portal")

        partner = self.env.ref("base.partner_demo_portal")
        test_task = self.env.ref("project.project_1_task_1")
        test_task.message_subscribe(partner.ids)

        task_type = test_task.stage_id
        task_type.name = "Test back-end stage name"

        # Base situation: no set portal_displayed_named
        task_type.portal_displayed_name = False

        response_1_html = self.url_open(self.base_url() + "/my/tasks").text

        self.assertIn(task_type.name, response_1_html)

        # Tasks page with a set portal_displayed_name
        task_type.portal_displayed_name = "Test portal displayed stage name"

        response_2_html = self.url_open(self.base_url() + "/my/tasks").text

        self.assertIn(task_type.portal_displayed_name, response_2_html)
        self.assertNotIn(task_type.name, response_2_html)

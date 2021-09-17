import mock
import requests
from odoo.tests.common import at_install, post_install

from .common import BaseShippingTC, pdf_page_num


@at_install(False)
@post_install(True)
class ProjectTaskTC(BaseShippingTC):
    def setUp(self):
        super(ProjectTaskTC, self).setUp()
        self.task = self.env.ref("project.project_task_1")
        self.task.project_id.shipping_account_id = self.shipping_account.id

    def test_print_parcel_actions(self):

        orig_task = self.task.with_context(mail_notrack=True)

        tasks = self.env["project.task"]
        for num in range(5):
            tasks += orig_task.copy({"name": "[SO%05d] Test lead" % num})

        ref = self.env.ref
        act_out = ref("commown_shipping.action_print_outward_fp2_label_task")

        with mock.patch.object(requests, "post", return_value=self.fake_resp):
            download_action = act_out.with_context(
                {"active_model": tasks._name, "active_ids": tasks.ids}
            ).run()

        all_labels = self._attachment_from_download_action(download_action)
        self.assertEqual(all_labels.name, self.parcel_type.name + ".pdf")
        self.assertEqual(pdf_page_num(all_labels), 2)

        act_ret = ref("commown_shipping.action_print_return_fp2_label_task")

        task = orig_task.copy({"name": "[Test single]"})
        with mock.patch.object(requests, "post", return_value=self.fake_resp):
            download_action = act_ret.with_context(
                {"active_model": tasks._name, "active_id": task.ids}
            ).run()

        label = self._attachment_from_download_action(download_action)

        self.assertEqualFakeLabel(label)

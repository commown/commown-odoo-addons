import requests_mock

from .common import BaseShippingTC, pdf_page_num


class ProjectTaskTC(BaseShippingTC):
    def setUp(self):
        super(ProjectTaskTC, self).setUp()
        self.task = self.env.ref("project.project_task_1")
        self.task.project_id.shipping_account_id = self.shipping_account.id

    def print_label(self, tasks, parcel_type, use_full_page_per_label=False):
        return self._print_label(
            "commown_shipping.task.print_label.wizard",
            tasks,
            parcel_type,
            use_full_page_per_label,
        )

    @requests_mock.Mocker()
    def test_print_parcel_actions(self, mocker):

        self.mock_colissimo_ok(mocker)

        orig_task = self.task.with_context(mail_notrack=True)

        tasks = self.env["project.task"]
        for num in range(5):
            tasks += orig_task.copy({"name": "[SO%05d] Test lead" % num})

        # Simulate two impressions in a row:
        all_labels_initial = self.print_label(tasks, self.parcel_type)
        all_labels = self.print_label(tasks, self.parcel_type)

        # Second impression must create new labels and delete the previous:
        self.assertTrue(all_labels_initial.ids != all_labels.ids)
        self.assertFalse(all_labels_initial.exists())

        self.assertEqual(all_labels.name, self.parcel_type.name + ".pdf")
        self.assertEqual(pdf_page_num(all_labels), 2)

        return_parcel_type = self.env["commown.parcel.type"].search(
            [("technical_name", "=", "fp2-return-ins300")],
        )
        task = orig_task.copy({"name": "[Test single]"})

        label = self.print_label(task, return_parcel_type, use_full_page_per_label=True)

        self.assertEqualFakeLabel(label)

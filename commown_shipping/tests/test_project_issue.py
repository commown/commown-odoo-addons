import requests
import mock

from odoo.tests.common import at_install, post_install

from .common import BaseShippingTC, pdf_page_num


@at_install(False)
@post_install(True)
class ProjectIssueTC(BaseShippingTC):

    def setUp(self):
        super(ProjectIssueTC, self).setUp()
        self.issue = self.env.ref(
            'project_issue.crm_case_buginaccountsmodule0')
        self.issue.project_id.update({
            'shipping_account_id': self.shipping_account.id
        })

    def test_print_parcel_actions(self):

        orig_issue = self.issue.with_context(mail_notrack=True)

        issues = self.env['project.issue']
        for num in range(5):
            issues += orig_issue.copy({
                'name': '[SO%05d] Test lead' % num,
            })

        ref = self.env.ref
        act_out = ref('commown_shipping.action_print_outward_fp2_label_issue')

        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            download_action = act_out.with_context({
                'active_model': issues._name, 'active_ids': issues.ids}).run()

        all_labels = self._attachment_from_download_action(download_action)
        self.assertEqual(all_labels.name, self.parcel_type.name + '.pdf')
        self.assertEqual(pdf_page_num(all_labels), 2)

        act_ret = ref('commown_shipping.action_print_return_fp2_label_issue')

        issue = orig_issue.copy({'name': '[Test single]'})
        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            download_action = act_ret.with_context({
                'active_model': issues._name, 'active_id': issue.ids}).run()

        label = self._attachment_from_download_action(download_action)

        self.assertEqualFakeLabel(label)

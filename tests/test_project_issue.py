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

    def test_parcel_labels(self):
        issues = self.env['project.issue']
        base_args = [self.parcel_type.name,
                     self.shipping_account.login,
                     self.env['res.partner'],  # empty sender!
                     self.issue.partner_id,
                     ]

        # avoid mail track bug in upcoming copies (confusion with project.task)
        orig_issue = self.issue.with_context(mail_notrack=True)

        for num in range(5):
            issue = orig_issue.copy({'name': 'Issue %d' % num})
            args = base_args + [issue.get_label_ref()]

            with mock.patch.object(
                    requests, 'post', return_value=self.fake_resp):
                issue._get_or_create_label(*args)

            issues += issue

        all_labels = issues.parcel_labels(*base_args)

        self.assertEqual(all_labels.name, self.parcel_type.name + '.pdf')
        self.assertEqual(pdf_page_num(all_labels), 2)

        issue = orig_issue.copy({'name': '[Test single]'})
        with mock.patch.object(requests, 'post', return_value=self.fake_resp):
            label = issue.parcel_labels(*base_args, force_single=True)

        self.assertEqualFakeLabel(label)

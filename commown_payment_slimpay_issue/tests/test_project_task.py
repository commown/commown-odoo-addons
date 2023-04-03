from odoo.tests.common import SavepointCase, at_install, post_install

from odoo.addons.payment_slimpay_issue.models.project_task import ProjectTask as PSIPT
from odoo.addons.payment_slimpay_issue.tests.test_project_task import ProjectTC

from ..models.project_task import ProjectTask as LocalPT


def _is_module_installed(cls, module_name):
    return cls.env["ir.module.module"].search_count(
        [
            ("name", "=", module_name),
            ("state", "=", "installed"),
        ]
    )


def _setUpClass(cls):
    """If present module is loaded (e.g. in the CI), monkey patch its
    ProjectTask class to let payment_slimpay_issue module's
    slimpay_payment_issue_process_automatically method show its
    effects in its tests.

    Also deactivate jobs as the present module uses them, which makes
    payment_slimpay_issue's tests fail without this monkey patch.
    """

    cls._old_setUpClass()
    if cls._is_module_installed("commown_payment_slimpay_issue"):
        cls._old_pt_slimpay_payment_issue_process_automatically = (
            LocalPT.slimpay_payment_issue_process_automatically
        )
        LocalPT.slimpay_payment_issue_process_automatically = (
            PSIPT.slimpay_payment_issue_process_automatically
        )

        cls.env = cls.env(
            context=dict(
                cls.env.context,
                test_queue_job_no_delay=True,
            )
        )


def _tearDownClass(cls):
    if cls._is_module_installed("commown_payment_slimpay_issue"):
        LocalPT.slimpay_payment_issue_process_automatically = (
            cls._old_pt_slimpay_payment_issue_process_automatically
        )


ProjectTC._is_module_installed = classmethod(_is_module_installed)
ProjectTC._old_setUpClass = ProjectTC.setUpClass
ProjectTC.setUpClass = classmethod(_setUpClass)
ProjectTC.tearDownClass = classmethod(_tearDownClass)


@at_install(False)
@post_install(True)
class ProjectTaskActionTC(SavepointCase):
    def test_payment_task_process_automatically(self):
        inv = (
            self.env["account.invoice"]
            .search([])
            .filtered(
                lambda i: i.invoice_line_ids
                and not any(line.contract_line_id for line in i.invoice_line_ids)
            )[0]
        )

        task = self.env["project.task"].create(
            {
                "name": "Test",
                "partner_id": self.env.ref("base.res_partner_3").id,
                "user_id": self.env.ref("base.user_demo").id,
                "invoice_id": inv.id,
            }
        )

        iline = inv.invoice_line_ids[0]

        self.assertFalse(task.slimpay_payment_issue_process_automatically())

        contract = self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": inv.partner_id.id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "line 1",
                            "product_id": iline.product_id.id,
                        },
                    )
                ],
            }
        )
        iline.contract_line_id = contract.contract_line_ids[0].id

        self.assertTrue(task.slimpay_payment_issue_process_automatically())

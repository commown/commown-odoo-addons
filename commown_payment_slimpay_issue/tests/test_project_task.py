from odoo.tests.common import SavepointCase, at_install, post_install


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

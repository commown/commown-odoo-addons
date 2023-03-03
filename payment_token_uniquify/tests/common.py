import contextlib

from odoo.tests.common import SavepointCase, tagged

from odoo.addons.queue_job.tests.common import trap_jobs


@tagged("post_install", "-at_install")
class PaymentTokenUniquifyTC(SavepointCase):
    def setUp(self):
        super().setUp()

        # A hierarchy of companies, main one has uniquify_token=False, the others True:
        self.company = self.new_company(uniquify_token=False)

        # - subcompany 1 with 2 workers:
        self.company_s1 = self.new_company(self.company, name="s1", uniquify_token=True)
        self.company_s1_w1 = self.new_worker(self.company_s1)
        self.company_s1_w2 = self.new_worker(self.company_s1)

        # - subcompany 2 with 2 workers and one subcompany...
        self.company_s2 = self.new_company(self.company, name="s2", uniquify_token=True)
        self.company_s2_w1 = self.new_worker(self.company_s2)
        self.company_s2_w2 = self.new_worker(self.company_s2)

    def new_worker(self, company, name="worker", **kwargs):
        kwargs.update({"name": name, "is_company": False, "parent_id": company.id})
        return self.env["res.partner"].create(kwargs)

    def new_company(self, parent=False, name="company", **kwargs):
        kwargs.update(
            {"name": name, "is_company": True, "parent_id": parent and parent.id},
        )
        return self.env["res.partner"].create(kwargs)

    def new_payment_token(self, partner, acquirer=None):
        if acquirer is None:
            acquirer = self.env.ref("payment.payment_acquirer_transfer")
        return self.env["payment.token"].create(
            {
                "name": "Token",
                "partner_id": partner.id,
                "acquirer_id": acquirer.id,
                "acquirer_ref": "test-acquirer-ref",
            }
        )

    @contextlib.contextmanager
    def _check_obsolete_token_action_job(self):
        with trap_jobs() as trap:
            new_token = yield trap
            yield
            job_method = new_token.acquirer_id.run_obsolete_token_actions
            trap.assert_jobs_count(1, only=job_method)
            trap.assert_enqueued_job(
                job_method,
                args=(new_token,),
                properties={"max_retries": 1},
            )
            trap.perform_enqueued_jobs()

import contextlib

from odoo.tests.common import SavepointCase, tagged

from odoo.addons.queue_job.tests.common import trap_jobs


@tagged("post_install", "-at_install")
class PaymentTokenUniquifyTC(SavepointCase):
    def setUp(self):
        super().setUp()

        # A hierarchy of companies:
        self.company = self.new_company()

        # - subcompany 1 with 2 workers:
        self.company_s1 = self.new_company(self.company, name="s1")
        self.company_s1_w1 = self.new_worker(self.company_s1, "s1_w1")
        self.company_s1_w2 = self.new_worker(self.company_s1, "s1_w2")

        # - subcompany 2 with 2 workers and one subcompany...
        self.company_s2 = self.new_company(self.company, name="s2")
        self.company_s2_w1 = self.new_worker(self.company_s2, "s2_w1")
        self.company_s2_w2 = self.new_worker(self.company_s2, "s2_w2")

    def new_worker(self, company, name="worker", **kwargs):
        kwargs.update({"name": name, "is_company": False, "parent_id": company.id})
        return self.env["res.partner"].create(kwargs)

    def new_company(self, parent=False, name="company", **kwargs):
        kwargs.update(
            {"name": name, "is_company": True, "parent_id": parent and parent.id},
        )
        return self.env["res.partner"].create(kwargs)

    def new_payment_token(self, partner, acquirer=None, set_as_partner_token=True):
        if acquirer is None:
            acquirer = self.env.ref("payment.payment_acquirer_transfer")
        token = self.env["payment.token"].create(
            {
                "name": "Token",
                "partner_id": partner.id,
                "acquirer_id": acquirer.id,
                "acquirer_ref": "test-acquirer-ref",
            }
        )
        if set_as_partner_token:
            partner.payment_token_id = token.id
        return token

    def _trigger_obsolescence(self, *action_refs, **new_partner_kwargs):
        """Trigger the tested code: a partner of the company creates a new token

        A payment acquirer is used that is first configured to trigger
        the token obsolescence actions passed as xml refs (without their
        common prefix).
        """
        acquirer = self.env.ref("payment.payment_acquirer_transfer")
        for action_ref in action_refs:
            if "." not in action_ref:
                action_ref = "commown.obsolescence_action_" + action_ref
            acquirer.obsolescence_action_ids |= self.env.ref(action_ref)

        new_partner_kwargs.setdefault("name", "s1_w3")
        company_s1_w3 = self.new_worker(self.company_s1, **new_partner_kwargs)
        cm = self._check_obsolete_token_action_job()
        with cm:
            new_token = self.new_payment_token(company_s1_w3, acquirer)
            cm.gen.send(new_token)
        return new_token

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

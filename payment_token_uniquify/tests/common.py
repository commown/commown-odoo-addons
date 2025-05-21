import contextlib

from odoo.tests import TransactionCase, tagged

from odoo.addons.queue_job.tests.common import trap_jobs


@tagged("post_install", "-at_install")
class PaymentTokenUniquifyTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # A hierarchy of companies:
        cls.company = cls.new_company()

        # - subcompany 1 with 2 workers:
        cls.company_s1 = cls.new_company(cls.company, name="s1")
        cls.company_s1_w1 = cls.new_worker(cls.company_s1, "s1_w1")
        cls.company_s1_w2 = cls.new_worker(cls.company_s1, "s1_w2")

        # - subcompany 2 with 2 workers and one subcompany...
        cls.company_s2 = cls.new_company(cls.company, name="s2")
        cls.company_s2_w1 = cls.new_worker(cls.company_s2, "s2_w1")
        cls.company_s2_w2 = cls.new_worker(cls.company_s2, "s2_w2")

    @classmethod
    def new_worker(cls, company, name="worker", **kwargs):
        kwargs.update({"name": name, "is_company": False, "parent_id": company.id})
        return cls.env["res.partner"].create(kwargs)

    @classmethod
    def new_company(cls, parent=False, name="company", **kwargs):
        kwargs.update(
            {"name": name, "is_company": True, "parent_id": parent and parent.id},
        )
        return cls.env["res.partner"].create(kwargs)

    @classmethod
    def new_payment_token(cls, partner, provider=None, set_as_partner_token=True):
        if provider is None:
            provider = cls.env.ref("payment.payment_provider_transfer")
        token = cls.env["payment.token"].create(
            {
                "partner_id": partner.id,
                "provider_id": provider.id,
                "provider_ref": "test-provider-ref",
            }
        )
        if set_as_partner_token:
            partner.payment_token_id = token.id
        return token

    def _trigger_obsolescence(self, *action_refs, **new_partner_kwargs):
        """Trigger the tested code: a partner of the company creates a new token

        A payment provider is used that is first configured to trigger
        the token obsolescence actions passed as xml refs (without their
        common prefix).
        """
        provider = self.env.ref("payment.payment_provider_transfer")
        for action_ref in action_refs:
            if "." not in action_ref:
                action_ref = "commown.obsolescence_action_" + action_ref
            provider.obsolescence_action_ids |= self.env.ref(action_ref)

        new_partner_kwargs.setdefault("name", "s1_w3")
        company_s1_w3 = self.new_worker(self.company_s1, **new_partner_kwargs)
        cm = self._check_obsolete_token_action_job()
        with cm:
            new_token = self.new_payment_token(company_s1_w3, provider)
            cm.gen.send(new_token)
        return new_token

    @contextlib.contextmanager
    def _check_obsolete_token_action_job(self):
        with trap_jobs() as trap:
            new_token = yield trap
            yield
            job_method = new_token.provider_id.run_obsolete_token_actions
            trap.assert_jobs_count(1, only=job_method)
            trap.assert_enqueued_job(
                job_method,
                args=(new_token,),
                properties={"max_retries": 1},
            )
            trap.perform_enqueued_jobs()

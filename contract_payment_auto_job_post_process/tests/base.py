from odoo import models


class TestTargetStateContextBase(models.AbstractModel):
    _inherit = "base"

    def _job_prepare_context_before_enqueue_keys(self):
        res = super()._job_prepare_context_before_enqueue_keys()
        return res + ("test_target_state",)

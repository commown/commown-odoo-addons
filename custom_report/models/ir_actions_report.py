from odoo import models


class IrActionsReport(models.Model):
    "Override methods called by portal to use py3o when useful"

    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        rep = self._get_report(report_ref)
        if (
            data
            and data.get("report_type") == "pdf"
            and rep.report_type == "py3o"
            and rep.py3o_filetype == "pdf"
        ):
            return self._render_py3o(report_ref, res_ids=res_ids, data=data)
        else:
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

from odoo import api, models


class IrActionsReport(models.Model):
    " Override methods called by portal to use py3o when useful "

    _inherit = 'ir.actions.report'

    @api.multi
    def render_qweb_pdf(self, res_ids=None, data=None):
        if (data and data.get("report_type") == "pdf"
                and self.report_type == "py3o" and self.py3o_filetype=="pdf"):
            return self.render_py3o(res_ids, data)
        else:
            return super().render_qweb_pdf(res_ids=res_ids, data=data)

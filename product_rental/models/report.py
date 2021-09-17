import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


class ProductRentalReport(models.Model):

    _inherit = 'report'

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        _logger.info('get_pdf called with docids=%s, report_name=%s, '
                     'html=%s, data=%s', docids, report_name, html, data)
        report = self._get_report_from_name(report_name)
        if report.report_type == 'py3o':
            # Let's generate the report and cache it in the db (if not already
            # done), so that further operations just return it
            context = dict(self.env.context)
            context['report_name'] = report_name
            py3o_report = self.env['py3o.report'].create({
                'ir_actions_report_xml_id': report.id
            })
            py3o_report.with_context(context).create_report(docids, data)
        return super(ProductRentalReport, self).get_pdf(
            docids, report_name, html, data)

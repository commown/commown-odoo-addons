import logging

from odoo.addons.report_py3o.models.py3o_report import py3o_report_extender

_logger = logging.getLogger(__name__)


@py3o_report_extender()
def py3o_extend(report_xml, localcontext):

    def translate(text, localcontext=localcontext, types=("code",)):
        env = localcontext["objects"].env
        lang = localcontext["lang"]
        result = env["ir.translation"]._get_source(
            'addons/custom_report/i18n/account_invoice.py', types, lang, text)
        _logger.debug(u"%s: %s > %s", lang, text, result)
        return result

    localcontext["_"] = translate

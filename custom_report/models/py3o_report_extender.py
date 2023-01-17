import logging

from odoo.addons.report_py3o.models.py3o_report import py3o_report_extender

_logger = logging.getLogger(__name__)


@py3o_report_extender()
def py3o_extend(report_xml, localcontext):
    def translate(text, localcontext=localcontext, types=("code",)):
        _logger.debug("LOCALCONTEXT: %s", localcontext)
        env = localcontext["objects"].env
        if localcontext.get("docs"):
            lang = localcontext["docs"][0].partner_id.lang
        else:
            lang = localcontext["lang"]
        result = env["ir.translation"]._get_source(
            "addons/custom_report/i18n/i18n.py", types, lang, text
        )
        _logger.debug("%s: %s > %s", lang, text, result)
        return result

    localcontext["_"] = translate

import logging

from odoo.tools.translate import code_translations

from odoo.addons.report_py3o.models.py3o_report import py3o_report_extender

_logger = logging.getLogger(__name__)


@py3o_report_extender()
def py3o_extend(report_xml, localcontext):
    def translate(text, localcontext=localcontext, types=("code",)):
        _logger.debug("LOCALCONTEXT: %s", localcontext)
        lang = (
            localcontext["docs"][0].partner_id.lang
            if localcontext.get("docs")
            else localcontext["lang"]
        )

        result = code_translations.get_python_translations("custom_report", lang).get(
            text, False
        )

        if result:
            _logger.debug("%s: %s > %s", lang, text, result)
        else:
            result = text
            _logger.debug("WARNING: %s not found in '%s' translations", text, lang)
        return result

    localcontext["_"] = translate

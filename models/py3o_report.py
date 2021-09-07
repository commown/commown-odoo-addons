from odoo.addons.report_py3o.models.py3o_report import py3o_report_extender


@py3o_report_extender()
def py3o_extend(report_xml, localcontext):

    def translate(text, localcontext=localcontext, types=("code",)):
        env = localcontext["objects"].env
        lang = localcontext["lang"]
        return env["ir.translation"]._get_source(
            'addons/custom_report/i18n/account_invoice.py', types, lang, text)

    localcontext["_"] = translate

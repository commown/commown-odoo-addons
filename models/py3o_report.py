from odoo.addons.report_py3o.models.py3o_report import py3o_report_extender


@py3o_report_extender()
def py3o_extend(report_xml, localcontext):

    def translate(text, localcontext=localcontext, types=("model",)):
        env = localcontext["objects"].env
        lang = localcontext["lang"]
        return env["ir.translation"]._get_source(
            'ir.ui.view,arch_db', types, lang, text)

    localcontext["_"] = translate

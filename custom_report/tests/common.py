import lxml.html

from odoo.tests.common import TransactionCase, tagged


def _html_report(report, obj, debug_fpath=None):
    html = report.render(obj.ids)[0]
    if debug_fpath:
        with open(debug_fpath, "wb") as fobj:
            fobj.write(html)
    return lxml.html.fromstring(html)


@tagged("-at_install", "post_install")
class ReportTC(TransactionCase):
    "Helper class for report tests"

    report_name = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Hack: reuse pdf report as an html one, to ease parsing
        cls.report = (
            cls.env["ir.actions.report"]
            ._get_report_from_name(cls.report_name)
            .ensure_one()
        )
        cls.report.py3o_filetype = "html"

    def html_report(self, entity, debug_fpath=None):
        return _html_report(self.report, entity, debug_fpath=debug_fpath)

    def h1(self, doc):
        return doc.xpath("normalize-space(//h1)")

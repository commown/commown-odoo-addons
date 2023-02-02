import lxml.html

from odoo.tests.common import TransactionCase, at_install, post_install

from odoo.addons.product_rental.tests.common import MockedEmptySessionMixin


def _html_report(report, obj, debug_fpath=None):
    html = report.render(obj.ids)[0]
    if debug_fpath:
        with open(debug_fpath, "wb") as fobj:
            fobj.write(html)
    return lxml.html.fromstring(html)


@at_install(False)
@post_install(True)
class ReportTC(MockedEmptySessionMixin, TransactionCase):
    "Helper class for report tests"

    report_name = None

    def setUp(self):
        super().setUp()

        # Hack: reuse pdf report as an html one, to ease parsing
        self.report = (
            self.env["ir.actions.report"]
            ._get_report_from_name(self.report_name)
            .ensure_one()
        )
        self.report.py3o_filetype = "html"

    def html_report(self, entity, debug_fpath=None):
        return _html_report(self.report, entity, debug_fpath=debug_fpath)

    def h1(self, doc):
        return doc.xpath("normalize-space(//h1)")

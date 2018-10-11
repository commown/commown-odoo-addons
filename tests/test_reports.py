import lxml.html

from odoo.tests.common import at_install, post_install
from . import common


@at_install(False)
@post_install(True)
class InvoiceReportTC(common.MockedEmptySessionTC):

    def setUp(self):
        super(InvoiceReportTC, self).setUp()
        self.b2c_partner = self.env.ref('portal.demo_user0_res_partner')
        self.b2b_partner = self.partner = self.env.ref('base.res_partner_2')

        deposit_account = self.env.ref('l10n_fr.1_pcg_2751')

        categ_deposit = self.env['product.category'].create({
            'name': 'Deposits',
            'type': 'normal',
            'property_account_income_categ_id': deposit_account,
            'property_account_expense_categ_id': deposit_account,
        })

        self.deposit_product = self.env['product.product'].create({
            'name': u'FP2 Premium', 'is_rental': True, 'type': 'service',
            'list_price': 60, 'categ_id': categ_deposit.id,
        })

        self.equity_product = self.env['product.product'].create({
            'name': u'Coop Part', 'is_equity': True, 'type': 'service',
            'list_price': 20,
        })

        self.std_product = self.env['product.product'].create({
            'name': u'Std product', 'type': 'service', 'list_price': 1,
        })

        # Hack: reuse pdf report as an html one, to ease parsing
        report_xml = self.env['py3o.report']._get_report_from_name(
            'account.report_invoice')
        report_xml.py3o_filetype = 'html'

    def sale(self, partner, products):
        olines = []
        for product in products:
            olines.append((0, 0, {
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'name': product.name,
                'product_uom_qty': 1,
                'price_unit': product.list_price,
            }))
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': olines,
        })
        so.action_confirm()
        return so

    def open_invoice(self, so, is_refund=False):
        inv = self.env['account.invoice'].browse(so.action_invoice_create())
        if is_refund:
            inv.type = 'out_refund'
        inv.action_invoice_open()
        return inv

    def html_invoice(self, partner, products, is_refund=False,
                     debug_fpath=None):
        inv = self.open_invoice(self.sale(partner, products), is_refund)
        html = self.env['py3o.report'].get_pdf(inv.mapped('id'),
                                               'account.report_invoice')
        if debug_fpath:
            with open(debug_fpath, 'wb') as fobj:
                fobj.write(html)
        return inv, lxml.html.fromstring(html)

    def test_b2c_deposit(self):
        inv, doc = self.html_invoice(self.b2c_partner, [self.deposit_product])
        self.assertEqual(doc.xpath('//h1/text()'),
                         ['Certificate %s' % inv.display_name.strip()])

    def test_b2c_equity(self):
        inv, doc = self.html_invoice(self.b2c_partner, [self.equity_product])
        self.assertEqual(doc.xpath('//h1/text()'),
                         ['Certificate %s' % inv.display_name.strip()])

    def test_b2c_std_product(self):
        inv, doc = self.html_invoice(self.b2c_partner, [self.std_product])
        self.assertEqual(doc.xpath('//h1/text()'),
                         ['Invoice %s' % inv.display_name.strip()])

    def test_b2c_refund(self):
        inv, doc = self.html_invoice(
            self.b2c_partner, [self.std_product], is_refund=True,
            debug_fpath='/tmp/invoice.html')
        self.assertEqual(doc.xpath('//h1/text()'),
                         ['Refund %s' % inv.display_name.strip()])

    def test_b2b_refund(self):
        inv, doc = self.html_invoice(
            self.b2c_partner, [self.std_product], is_refund=True,
            debug_fpath='/tmp/invoice.html')
        self.assertEqual(doc.xpath('//h1/text()'),
                         ['Refund %s' % inv.display_name.strip()])

    def test_b2b_deposit(self):
        inv, doc = self.html_invoice(self.b2b_partner, [self.deposit_product])
        self.assertEqual(doc.xpath('//h1/text()'),
                         ['Invoice %s' % inv.display_name.strip()])

    def test_b2b_std_product(self):
        inv, doc = self.html_invoice(self.b2b_partner, [self.std_product])
        self.assertEqual(doc.xpath('//h1/text()'),
                         ['Invoice %s' % inv.display_name.strip()])

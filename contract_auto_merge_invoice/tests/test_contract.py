from odoo.addons.contract.tests.test_contract import TestContractBase

from odoo.tests.common import at_install, post_install


@at_install(False)
@post_install(True)
class ContractTC(TestContractBase):

    def test_auto_merge_invoice(self):
        # TODO, FIXME
        return
        invoice = self.contract.recurring_create_invoice()
        self.assertTrue(invoice.auto_merge)

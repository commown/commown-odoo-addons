from odoo.addons.contract.tests.test_contract import TestContractBase

from mock import patch

from odoo.tests.common import at_install, post_install


@at_install(False)
@post_install(True)
class ContractPaymentTC(TestContractBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        slimpay = cls.env['payment.acquirer'].search(
            [('provider', '=', 'slimpay')]).ensure_one()
        payment_token = cls.env['payment.token'].create({
            'name': 'Test Slimpay Token',
            'partner_id': cls.contract.partner_id.id,
            'active': True,
            'acquirer_id': slimpay.id,
            'acquirer_ref': 'Slimpay mandate ref',
        })
        cls.contract.update({
            'payment_token_id': payment_token.id,
            'is_auto_pay': True,
        })

    def setUp(self):
        super().setUp()
        client_patcher = patch('odoo.addons.account_payment_slimpay.models.'
                               'slimpay_utils.get_client')
        client_patcher.start()
        self.addCleanup(client_patcher.stop)

    def test_default_payin_label(self):
        with patch('odoo.addons.account_payment_slimpay.models.'
                   'slimpay_utils.SlimpayClient.create_payment') as pay:
            invoice = self.contract.recurring_create_invoice()
            label = pay.call_args[0][-1]
            self.assertEqual(label, invoice.number)

    def test_custom_payin_label(self):
        self.contract.write({
            'transaction_label': 'Invoice #INV# - #DATE#',
            'recurring_next_date': '2018-02-15',
        })
        with patch('odoo.addons.account_payment_slimpay.models.'
                   'slimpay_utils.SlimpayClient.create_payment') as pay:
            invoice = self.contract.recurring_create_invoice()
            label = pay.call_args[0][-1]
            self.assertEqual(label, 'Invoice %s - 02/15/2018' % invoice.number)

import logging

import requests

from odoo import models, api, fields, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


def reject_date(issue_doc):
    return issue_doc['dateCreated'].split('T', 1)[0]


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    invoice_id = fields.Many2one('account.invoice', string='Invoice')
    invoice_unpaid_count = fields.Integer(
        'Number of payment issues', default=0)

    @api.model
    def _slimpay_payment_max_retrials(self):
        """ Return the number of automatic retrials before deciding to handle
        an issue manually.
        """
        return int(self.env['ir.config_parameter'].get_param(
            'payment_slimpay_issue.max_retrials') or 2)

    @api.model
    def _slimpay_payment_invoice_fee_after_trial_number(self):
        """ Return the number of payment retrials before applying fees. Use 0
        to apply fees at first payment issue.
        """
        return int(self.env['ir.config_parameter'].get_param(
            'payment_slimpay_issue.invoice_fee_after_trial_number') or 1)

    @api.model
    def _slimpay_payment_invoice_prefix(self):
        """ Return the invoice number prefix to filter payment transactions
        which reference an invoice. """
        Journal = self.env['account.journal']
        Invoice = self.env['account.invoice']

        journal_id = Invoice.default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('No sale journal defined for this company.'))
        inv_journal = Journal.browse(journal_id)
        return inv_journal.sequence_id.prefix.split('%', 1)[0]

    @api.model
    def _slimpay_payment_issue_cron(self, custom_issue_params=None):

        """ Regular cron task entry point, that fetches the issues of each
        website-published Slimpay acquirer, handle them in odoo and then
        sets their status to "processed" at Slimpay.
        """

        for acquirer in self.env['payment.acquirer'].search([
                ('provider', '=', 'slimpay')]):
            _logger.info(u'Checking payment issues for "%s"' % acquirer.name)

            try:
                client = acquirer.slimpay_client
            except requests.HTTPError:
                # Invalid credentials error must not crash the transaction
                # (one may have more than one slimpay acquirer activated
                #  or not in an environment or another -prod or debug-)
                continue

            for num, issue_doc in enumerate(self._slimpay_payment_issue_fetch(
                    client, **(custom_issue_params or {}))):
                _logger.debug('Handling Slimpay issue id %s', issue_doc['id'])
                if not num:
                    project = self.env.ref(
                        'payment_slimpay_issue.project_payment_issue')
                    inv_prefix = self._slimpay_payment_invoice_prefix()
                self._slimpay_payment_issue_handle(
                    project, client, issue_doc, inv_prefix)
                _logger.debug('Ack Slimpay issue id %s', issue_doc['id'])
                self._slimpay_payment_issue_ack(client, issue_doc)

    @api.model
    def _slimpay_payment_issue_ack(self, client, issue_doc):
        """ Set a Slimpay issue designated by given document as processed """
        doc = client.action('POST', 'ack-payment-issue', doc=issue_doc)
        assert doc['executionStatus'] == u'processed'
        _logger.debug('Issue id %s marked as processed', issue_doc['id'])

    @api.model
    def _slimpay_payment_issue_fetch(self, client, page=0, **custom_params):
        """ Fetch issues in the 'toprocess' state using Slimpay API given
        `client`, starting at `page` (0 by default), and yield the
        Slimpay API issue documents one after an other.

        Keyword arguments can be used to override Slimpay issue search
        API params, in particular the executionStatus, for e.g. debug
        purposes.
        """

        params = {
            'creditorReference': client.creditor,
            'scheme': 'SEPA.DIRECT_DEBIT.CORE',
            'executionStatus': 'toprocess',
            'page': page,
        }
        params.update(custom_params)
        doc = client.action('GET', 'search-payment-issues', params=params)

        _logger.debug('Slimpay issues doc:\n%s', doc)

        for issue_doc in doc.data.get('paymentIssues', ()):
            yield issue_doc
        if 'next' in doc:
            for issue_doc in self._slimpay_payment_issue_fetch(
                    client, page+1, **custom_params):
                yield issue_doc

    @api.model
    def _slimpay_payment_issue_find_invoice(self, issue_doc, payment_doc,
                                            inv_prefix):
        # XXX Fix this in payment_slimpay and report here
        # (idea: use a Slimpay-generated ref and put it in acquirer_reference
        #  then use this field's value to find the right transaction)
        if (payment_doc['reference']
                and payment_doc['reference'].startswith('TR')):
            try:
                tr_id = int(payment_doc['reference'][2:])
                ref = self.env['payment.transaction'].browse(tr_id).reference
            except:
                pass
            else:
                if ref and ref.startswith(inv_prefix):
                    return self.env['account.invoice'].search([
                        ('number', '=', ref.split('x', 1)[0])])

    @api.model
    def _slimpay_payment_issue_get_or_create(self, project, client, issue_doc,
                                             inv_prefix):
        meth = client.method_name
        payment_doc = client.get(issue_doc[meth('get-payment')].url)

        name = [reject_date(issue_doc),
                '%s %s' % (issue_doc['rejectAmount'], issue_doc['currency']),
                ]
        partner_id = False
        invoice = self._slimpay_payment_issue_find_invoice(
            issue_doc, payment_doc, inv_prefix)
        if invoice:
            existing = self.env['project.issue'].search([
                ('project_id', '=', project.id),
                ('invoice_id', '=', invoice.id),
            ])
            if existing:
                return existing[0]
            partner_id = invoice.partner_id.id
            name.append(invoice.number)
        else:
            subscriber_doc = client.get(
                payment_doc[meth('get-subscriber')].url)
            try:
                _pid = int(subscriber_doc['reference'])
            except:
                pass
            else:
                partner = self.env['res.partner'].search([('id', '=', _pid)])
                if partner:
                    partner_id = _pid

        description = [
            u'Slimpay Id: %s' % issue_doc['id'],
            u'Payment Reference: %s' % payment_doc['reference'],
            u'Payment Label: %s' % payment_doc['label'],
        ]

        return self.env['project.issue'].create({
            'name': u' - '.join(name),
            'description': u'\n'.join(description),
            'project_id': project.id,
            'partner_id': partner_id,
            'invoice_id': invoice.id if invoice else False,
        })

    @api.model
    def _slimpay_payment_issue_invoice_reject_fees(self, invoice, reject_date):
        prod = self.env.ref('payment_slimpay_issue.'
                            'rejected_sepa_fee_product').product_variant_id
        _logger.debug('Adding reject fees to %s invoice amount %s...',
                      invoice.state, invoice.amount_total)

        invoice.action_invoice_cancel()
        self.env.invalidate_all  # XXX update invoice.state cache (?)
        invoice.action_invoice_draft()

        invoice.update({'invoice_line_ids': [(0, 0, {
            'name': prod.name,
            'product_id': prod.id,
            'price_unit': prod.list_price,
            'account_id': prod.property_account_income_id.id,
        })]})

        invoice.action_invoice_open()

        _logger.debug('... new amount is %s, state %s',
                      invoice.amount_total, invoice.state)

    @api.multi
    def _slimpay_payment_issue_retry_payment(self):
        Transaction = self.env['payment.transaction']
        for issue in self:
            invoice = issue.invoice_id
            partner = invoice.partner_id
            token = partner.payment_token_ids[0]

            _logger.info(
                'Issue %s: retrying payment of invoice %s of %s with %s',
                issue.id, invoice.number, partner.name, token.name)

            transaction = Transaction.create({
                'reference': Transaction.get_next_reference(invoice.number),
                'acquirer_id': token.acquirer_id.id,
                'payment_token_id': token.id,
                'amount': invoice.residual,
                'state': 'draft',
                'currency_id': invoice.currency_id.id,
                'partner_id': partner.id,
                'partner_country_id': partner.country_id.id,
                'partner_city': partner.city,
                'partner_zip': partner.zip,
                'partner_email': partner.email,
            })

            payment_mode = invoice.payment_mode_id
            payment = self.env['account.payment'].create({
                'company_id': issue.user_id.company_id.id,
                'partner_id': invoice.partner_id.id,
                'partner_type': 'customer',
                'state': 'draft',
                'payment_type': 'inbound',
                'journal_id': payment_mode.fixed_journal_id.id,
                'payment_method_id': payment_mode.payment_method_id.id,
                'amount': invoice.residual,
                'payment_transaction_id': transaction.id,
                'invoice_ids': [(6, 0, [invoice.id])],
            })
            payment.post()

            if not transaction.s2s_do_transaction():
                _logger.error('Transaction %s failed', transaction.id)

    @api.model
    def _slimpay_payment_issue_handle(self, project, client, issue_doc,
                                      inv_prefix):
        issue = self._slimpay_payment_issue_get_or_create(
            project, client, issue_doc, inv_prefix)

        # No related invoice: move to orphan stage and exit
        if not issue.invoice_id:
            issue.update({'stage_id': self.env.ref(
                'payment_slimpay_issue.stage_orphan').id})
            return

        issue.invoice_unpaid_count += 1
        issue.invoice_id.payment_move_line_ids.remove_move_reconcile()

        if (issue.invoice_unpaid_count
                > self._slimpay_payment_invoice_fee_after_trial_number()):
            self._slimpay_payment_issue_invoice_reject_fees(
                issue.invoice_id, reject_date(issue_doc))

        if issue.invoice_unpaid_count > self._slimpay_payment_max_retrials():
            issue.update({'stage_id': self.env.ref(
                'payment_slimpay_issue.stage_max_trials_reached').id})
        else:
            issue.update({'stage_id': self.env.ref(
                'payment_slimpay_issue.stage_warn_partner_and_wait').id})

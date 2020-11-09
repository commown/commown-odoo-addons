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
    invoice_next_payment_date = fields.Date(
        'Invoice next payment date', help=(
            'If set in the future, the next payment trial (if any) will occur'
            ' at this date'))
    slimpay_payment_label = fields.Text(
        'Slimpay payment label', help=(
            'Label the customer will see on his bank statement.'
            ' When left empty, the Odoo transaction name will appear.'))

    @api.model
    def _slimpay_payment_invoice_payment_next_date_days_delta(self):
        """ Return the number of days the next payment trial will occur
        after the partner has been warned.
        """
        return int(self.env['ir.config_parameter'].get_param(
            'payment_slimpay_issue.payment_retry_after_days_number') or 5)

    @api.model
    def _slimpay_payment_max_retrials(self):
        """ Return the number of automatic retrials before deciding to handle
        an issue manually.
        """
        return int(self.env['ir.config_parameter'].get_param(
            'payment_slimpay_issue.max_retrials') or 2)

    @api.model
    def _slimpay_payment_issue_management_fees_retrial_num(self):
        """ Return the number of payment retrials before applying management
        fees. Use 0 to apply management fees at first payment issue.
        """
        return int(self.env['ir.config_parameter'].get_param(
            'payment_slimpay_issue.management_fees_after_retrial_number') or 1)

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
    def _slimpay_payment_issue_single_issue(self, project, client, issue_doc,
                                                inv_prefix):
        """Handle DB updates and HTTP transaction individually so that if one
        Slimpay HTTP ack fails, only the corresponding DB updates are
        rolled back. This uses DB save point as a mecanism, but could
        be easily overriden to use a job queue.
        """
        try:
            with self.env.cr.savepoint():
                if issue_doc.get('rejectReason', None) != \
                       'sepaReturnReasonCode.focr.reason':
                    issue = self._slimpay_payment_issue_handle(
                        project, client, issue_doc, inv_prefix)
                else:
                    _logger.info(
                        'Slimpay payment cancelled by creditor id %s: will be'
                        ' definitively ignored (ack coming)', issue_doc['id'])
                _logger.debug('Ack Slimpay issue id %s', issue_doc['id'])
                self._slimpay_payment_issue_ack(client, issue_doc)
        except:
            _logger.exception(
                'Error occurred while handling payment issue %s (see below).'
                'Everything concerning this specific issue has been'
                ' cleanly rolled back. Trying to continue with other issues!',
                issue_doc['id'])

    @api.model
    def _slimpay_payment_issue_cron(self, custom_issue_params=None):

        """ Regular cron task entry point, that fetches the issues of each
        website-published Slimpay acquirer, handle them in odoo and then
        sets their status to "processed" at Slimpay.
        """

        for acquirer in self.env['payment.acquirer'].search([
                ('provider', '=', 'slimpay')]):
            _logger.info('Checking payment issues for "%s"', acquirer.name)

            try:
                client = acquirer.slimpay_client
            except requests.HTTPError:
                # Invalid credentials error must not crash the transaction
                # (one may have more than one slimpay acquirer activated
                #  or not in an environment or another -prod or debug-)
                continue

            issues = list(self._slimpay_payment_issue_fetch(
                client, **(custom_issue_params or {})))
            for num, issue_doc in enumerate(issues):
                _logger.debug('Handling Slimpay issue id %s', issue_doc['id'])
                if not num:
                    project = self.env.ref(
                        'payment_slimpay_issue.project_payment_issue')
                    inv_prefix = self._slimpay_payment_invoice_prefix()
                self._slimpay_payment_issue_single_issue(project, client,
                                                         issue_doc, inv_prefix)
    @api.model
    def _slimpay_payment_issue_ack(self, client, issue_doc):
        """ Set a Slimpay issue designated by given document as processed """
        doc = client.action('POST', 'ack-payment-issue', doc=issue_doc)
        assert doc['executionStatus'] == 'processed'
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
    def _slimpay_payment_issue_find_invoice(
            self, issue_doc, payment_doc, inv_prefix):
        tr_ref = payment_doc['id']
        try:
            tr_ref = payment_doc['reference']
            tr = self.env['payment.transaction'].search([
                ('acquirer_reference', '=', tr_ref),
            ]).ensure_one()
        except:
            _logger.warning('Could not find Odoo transaction for'
                            ' Slimpay payment %r', tr_ref)
        else:
            ref = tr.reference
            if ref and ref.startswith(inv_prefix):
                return self.env['account.invoice'].search([
                    ('number', '=', ref.split('x', 1)[0])])

    @api.model
    def _slimpay_payment_issue_name(self, issue_doc, payment_doc,
                                       invoice=None, issue=None):
        if issue is None:
            name = [
                payment_doc['reference'] or _('No payment ref'),
                reject_date(issue_doc),
                '%s %s' % (issue_doc['rejectAmount'], issue_doc['currency']),
            ]
            if invoice is not None:
                name.append(invoice.number)
        else:
            name = [payment_doc['reference'], issue.name]
        return ' - '.join(name)

    @api.model
    def _slimpay_payment_issue_get_or_create(self, project, client, issue_doc,
                                             inv_prefix):
        meth = client.method_name
        payment_doc = client.get(issue_doc[meth('get-payment')].url)

        partner_id = False
        invoice = self._slimpay_payment_issue_find_invoice(
            issue_doc, payment_doc, inv_prefix)
        if invoice:
            existing = self.env['project.issue'].search([
                ('project_id', '=', project.id),
                ('invoice_id', '=', invoice.id),
            ])
            if existing:
                existing[0].name = self._slimpay_payment_issue_name(
                    issue_doc, payment_doc, invoice, existing[0])
                return existing[0]
            partner_id = invoice.partner_id.id
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
            'Slimpay Id: %s' % issue_doc['id'],
        ]

        return self.env['project.issue'].create({
            'name': self._slimpay_payment_issue_name(
                issue_doc, payment_doc, invoice),
            'description': '\n'.join(description),
            'project_id': project.id,
            'partner_id': partner_id,
            'invoice_id': invoice.id if invoice else False,
            'slimpay_payment_label': payment_doc['label'],
        })

    def slimpay_payment_issue_process_automatically(self):
        """Override this if you want special rules to deny automatic
        processing of some issues.

        The default implementation handles basically all issues for
        which an invoice has been found.

        """
        self.ensure_one()
        return bool(self.invoice_id)

    @api.model
    def _slimpay_payment_issue_fees_product(self, type):
        try:
            return self.env.ref('payment_slimpay_issue.'
                                '%s_fees_product' % type).product_variant_id
        except ValueError:
            _logger.info('No %s fees product found', fees_name)

    @api.model
    def _slimpay_payment_issue_invoice_fees(
            self, invoice, fees_name, amount=None):
        product = self._slimpay_payment_issue_fees_product(fees_name)
        if not product:
            return

        _logger.info('Adding %s fees to %s invoice amount %s...',
                     fees_name, invoice.state, invoice.amount_total)

        invoice.action_invoice_cancel()
        invoice.action_invoice_draft()

        invoice.update({'invoice_line_ids': [(0, 0, {
            'name': product.name,
            'product_id': product.id,
            'price_unit': amount or product.list_price,
            'account_id': product.property_account_income_id.id,
            'invoice_line_tax_ids': [(6, 0, product.taxes_id.ids)],
        })]})
        invoice._onchange_invoice_line_ids()

        invoice.action_invoice_open()

        _logger.debug('... new amount is %s, state %s',
                      invoice.amount_total, invoice.state)

    @api.model
    def _slimpay_payment_issue_create_supplier_invoice_fees(
            self, reference, date, amount):
        slimpay_fees_partner = self.env.ref(
            'payment_slimpay_issue.slimpay_fees_partner')
        product = self.env.ref(
            'payment_slimpay_issue.bank_supplier_fees_product'
        ).product_variant_ids
        if not product:
            _logger.info('Issue %s: No bank supplier fees product:'
                         ' skipping fees invoice creation', self.id)
            return
        invoice = self.env['account.invoice'].create({
            'type': 'in_invoice',
            'partner_id': slimpay_fees_partner.id,
            'reference': reference,
            'date_invoice': date,
            'invoice_line_ids': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'price_unit': amount,
                'account_id': product.property_account_expense_id.id,
                'invoice_line_tax_ids': [(6, 0, product.supplier_taxes_id.ids)],
            })],
        })
        invoice._onchange_invoice_line_ids()
        invoice.action_invoice_open()

    @api.multi
    def _slimpay_payment_issue_retry_payment(self):
        Transaction = self.env['payment.transaction']
        for issue in self:
            invoice = issue.invoice_id
            partner = invoice.partner_id

            if not partner.payment_token_ids:
                _logger.error(
                    'Invoice %s: partner has no payment token!', invoice.id)
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

            if self.slimpay_payment_label:
                transaction = transaction.with_context(
                    slimpay_payin_label=self.slimpay_payment_label)

            if not transaction.s2s_do_transaction():
                _logger.error('Transaction %s failed', transaction.id)

    @api.model
    def _slimpay_payment_issue_handle(self, project, client, issue_doc,
                                         inv_prefix):
        issue = self._slimpay_payment_issue_get_or_create(
            project, client, issue_doc, inv_prefix)
        invoice = issue.invoice_id

        # No related invoice: move to orphan stage and exit
        if not issue.slimpay_payment_issue_process_automatically():
            issue.update({'stage_id': self.env.ref(
                'payment_slimpay_issue.stage_orphan').id})
            return

        issue.invoice_unpaid_count += 1

        _logger.info('Unreconciling invoice "%s"', invoice.name)
        invoice.payment_move_line_ids.remove_move_reconcile()
        _logger.info('Invoice payments "%s"', invoice.payment_ids.ids)
        for payment in invoice.payment_ids:
            _logger.info('Canceling payment "%s"', payment.id)
            payment.cancel()

        rejected_amount = float(issue_doc['rejectAmount'])
        if invoice.amount_total < rejected_amount:
            fees = rejected_amount - invoice.amount_total
            self._slimpay_payment_issue_invoice_fees(invoice, 'bank', fees)
            self._slimpay_payment_issue_create_supplier_invoice_fees(
                '%s-REJ%d' % (invoice.number, issue.invoice_unpaid_count),
                reject_date(issue_doc), fees)

        if (issue.invoice_unpaid_count
                > self._slimpay_payment_issue_management_fees_retrial_num()):
            self._slimpay_payment_issue_invoice_fees(invoice, 'management')

        if issue.invoice_unpaid_count > self._slimpay_payment_max_retrials():
            issue.update({'stage_id': self.env.ref(
                'payment_slimpay_issue.stage_max_trials_reached').id})
        else:
            issue.update({'stage_id': self.env.ref(
                'payment_slimpay_issue.stage_warn_partner_and_wait').id})
        return issue

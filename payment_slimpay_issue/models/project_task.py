import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone

from .utils import SLIMPAY_ERROR_CODES

_logger = logging.getLogger(__name__)


def reject_date(issue_doc):
    return issue_doc["dateCreated"].split("T", 1)[0]


class ProjectTask(models.Model):
    _inherit = "project.task"

    invoice_id = fields.Many2one("account.move", string="Invoice")
    invoice_unpaid_count = fields.Integer("Number of payment issues", default=0)
    invoice_next_payment_date = fields.Date(
        "Invoice next payment date",
        help=(
            "If set in the future, the next payment trial (if any) will occur"
            " at this date"
        ),
    )
    slimpay_payment_label = fields.Text(
        "Slimpay payment label",
        help=(
            "Label the customer will see on his bank statement."
            " When left empty, the Odoo transaction name will appear."
        ),
    )

    @api.model
    def _slimpay_payment_invoice_payment_next_date_days_delta(self):
        """Return the number of days the next payment trial will occur
        after the partner has been warned.
        """
        return int(
            self.env["ir.config_parameter"].get_param(
                "payment_slimpay_issue.payment_retry_after_days_number"
            )
            or 5
        )

    @api.model
    def _slimpay_payment_max_retrials(self):
        """Return the number of automatic retrials before deciding to handle
        an issue manually.
        """
        return int(
            self.env["ir.config_parameter"].get_param(
                "payment_slimpay_issue.max_retrials"
            )
            or 2
        )

    @api.model
    def _slimpay_payment_issue_management_fees_retrial_num(self):
        """Return the number of payment retrials before applying management
        fees. Use 0 to apply management fees at first payment issue.
        """
        return int(
            self.env["ir.config_parameter"].get_param(
                "payment_slimpay_issue.management_fees_after_retrial_number"
            )
            or 1
        )

    @api.model
    def _slimpay_payment_issue_single_issue(self, project, client, issue_doc):
        """Handle DB updates and HTTP transaction individually so that if one
        Slimpay HTTP ack fails, only the corresponding DB updates are
        rolled back. This uses DB save point as a mecanism, but could
        be easily overriden to use a job queue.
        """
        try:
            with self.env.cr.savepoint():
                if (
                    issue_doc.get("rejectReason", None)
                    != "sepaReturnReasonCode.focr.reason"
                ):
                    self._slimpay_payment_issue_handle(project, client, issue_doc)
                else:
                    _logger.info(
                        "Slimpay payment cancelled by creditor id %s: will be"
                        " definitively ignored (ack coming)",
                        issue_doc["id"],
                    )
                _logger.debug("Ack Slimpay issue id %s", issue_doc["id"])
                self._slimpay_payment_issue_ack(client, issue_doc)
        except Exception:
            _logger.exception(
                "Error occurred while handling payment issue %s (see below)."
                "Everything concerning this specific issue has been"
                " cleanly rolled back. Trying to continue with other issues!",
                issue_doc["id"],
            )

    @api.model
    def _slimpay_payment_issue_cron(self, custom_issue_params=None):

        """Regular cron task entry point, that fetches the issues of each
        website-published Slimpay acquirer, handle them in odoo and then
        sets their status to "processed" at Slimpay.
        """

        for provider in self.env["payment.provider"].search(
            [("code", "=", "slimpay"), ("state", "=", "enabled")],
        ):
            _logger.info('Checking payment issues for "%s"', provider.name)

            try:
                client = provider.slimpay_client()
            except requests.HTTPError:
                # Invalid credentials error must not crash the transaction
                # (one may have more than one slimpay provider activated
                #  or not in an environment or another -prod or debug-)
                continue

            issues = list(
                self._slimpay_payment_issue_fetch(client, **(custom_issue_params or {}))
            )
            for num, issue_doc in enumerate(issues):
                _logger.debug("Handling Slimpay issue id %s", issue_doc["id"])
                if not num:
                    project = self.env.ref(
                        "payment_slimpay_issue.project_payment_issue"
                    )
                self._slimpay_payment_issue_single_issue(project, client, issue_doc)

    @api.model
    def _slimpay_payment_issue_ack(self, client, issue_doc):
        """Set a Slimpay issue designated by given document as processed"""
        doc = client.action("POST", "ack-payment-issue", doc=issue_doc)
        assert doc["executionStatus"] == "processed"
        _logger.debug("Issue id %s marked as processed", issue_doc["id"])

    @api.model
    def _slimpay_payment_issue_fetch(self, client, page=0, **custom_params):
        """Fetch issues in the 'toprocess' state using Slimpay API given
        `client`, starting at `page` (0 by default), and yield the
        Slimpay API issue documents one after an other.

        Keyword arguments can be used to override Slimpay issue search
        API params, in particular the executionStatus, for e.g. debug
        purposes.
        """

        params = {
            "creditorReference": client.creditor,
            "scheme": "SEPA.DIRECT_DEBIT.CORE",
            "executionStatus": "toprocess",
            "page": page,
        }
        params.update(custom_params)
        doc = client.action("GET", "search-payment-issues", params=params)

        _logger.debug("Slimpay issues doc:\n%s", doc)

        for issue_doc in doc.data.get("paymentIssues", ()):
            yield issue_doc
        if "next" in doc:
            for issue_doc in self._slimpay_payment_issue_fetch(
                client, page + 1, **custom_params
            ):
                yield issue_doc

    @api.model
    def _slimpay_payment_issue_find_invoice(self, issue_doc, payment_doc):
        tr_ref = payment_doc["id"]
        tr_model = self.env["payment.transaction"]
        try:
            tr_ref = payment_doc["reference"]
            tr = tr_model.search([("provider_reference", "=", tr_ref)]).ensure_one()
        except Exception:
            _logger.info(
                "Could not find Odoo transaction for" " Slimpay payment %r", tr_ref
            )
        else:
            return tr.invoice_ids and tr.invoice_ids[0]

    @api.model
    def _slimpay_payment_issue_name(
        self, issue_doc, payment_doc, invoice=None, task=None
    ):
        if task is None:
            name = [
                payment_doc["reference"] or _("No payment ref"),
                reject_date(issue_doc),
                "%s %s" % (issue_doc["rejectAmount"], issue_doc["currency"]),
            ]
            if invoice:
                name.append(invoice.name)
        else:
            name = [payment_doc["reference"], task.name]
        return " - ".join(name)

    @api.model
    def _slimpay_payment_issue_get_or_create(self, project, client, issue_doc):
        meth = client.method_name
        payment_doc = client.get(issue_doc[meth("get-payment")].url)

        partner_id = False
        invoice = self._slimpay_payment_issue_find_invoice(issue_doc, payment_doc)
        if invoice:
            existing = self.env["project.task"].search(
                [
                    ("project_id", "=", project.id),
                    ("invoice_id", "=", invoice.id),
                ]
            )
            if existing:
                existing[0].name = self._slimpay_payment_issue_name(
                    issue_doc, payment_doc, invoice, existing[0]
                )
                return existing[0]
            partner_id = invoice.partner_id.id
        else:
            subscriber_doc = client.get(payment_doc[meth("get-subscriber")].url)
            try:
                _pid = int(subscriber_doc["reference"])
            except Exception:  # pylint: disable=except-pass
                pass
            else:
                partner = self.env["res.partner"].search([("id", "=", _pid)])
                if partner:
                    partner_id = _pid

        description = [
            "Slimpay Id: %s" % issue_doc["id"],
        ]

        return self.env["project.task"].create(
            {
                "name": self._slimpay_payment_issue_name(
                    issue_doc, payment_doc, invoice
                ),
                "description": "\n".join(description),
                "project_id": project.id,
                "partner_id": partner_id,
                "invoice_id": invoice.id if invoice else False,
                "slimpay_payment_label": payment_doc["label"],
            }
        )

    def slimpay_payment_issue_process_automatically(self):
        """Override this if you want special rules to deny automatic
        processing of some issues.

        The default implementation handles basically all issues for
        which an invoice has been found.

        """
        self.ensure_one()
        pay_meth = self.invoice_id.payment_mode_id.payment_method_id
        return pay_meth.payment_type == "inbound" and pay_meth.code == "electronic"

    @api.model
    def _slimpay_payment_issue_fees_product(self, fees_name):
        try:
            return self.env.ref(
                "payment_slimpay_issue." "%s_fees_product" % fees_name
            ).product_variant_id
        except ValueError:
            _logger.info("No %s fees product found", fees_name)

    @api.model
    def _slimpay_payment_issue_invoice_fees(self, invoice, fees_name, amount=None):
        product = self._slimpay_payment_issue_fees_product(fees_name)
        if not product:
            return

        _logger.info(
            "Adding %s fees to %s invoice amount %s...",
            fees_name,
            invoice.state,
            invoice.amount_total,
        )

        invoice.action_invoice_cancel()
        invoice.action_invoice_draft()

        invoice.update(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "price_unit": amount or product.list_price,
                            "account_id": product.property_account_income_id.id,
                            "invoice_line_tax_ids": [(6, 0, product.taxes_id.ids)],
                        },
                    )
                ]
            }
        )
        invoice._onchange_invoice_line_ids()

        invoice.action_invoice_open()

        _logger.debug(
            "... new amount is %s, state %s", invoice.amount_total, invoice.state
        )

    @api.model
    def _slimpay_payment_issue_create_supplier_invoice_fees(
        self, reference, date, amount
    ):
        slimpay_fees_partner = self.env.ref(
            "payment_slimpay_issue.slimpay_fees_partner"
        )
        product = self.env.ref(
            "payment_slimpay_issue.bank_supplier_fees_product"
        ).product_variant_ids
        if not product:
            _logger.info(
                "Task %s: No bank supplier fees product:"
                " skipping fees invoice creation",
                self.id,
            )
            return
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": slimpay_fees_partner.id,
                "ref": reference,
                "invoice_date": date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "price_unit": amount,
                            "account_id": product.property_account_expense_id.id,
                            "invoice_line_tax_ids": [
                                (6, 0, product.supplier_taxes_id.ids)
                            ],
                        },
                    )
                ],
            }
        )
        invoice.action_post()

    def _slimpay_payment_issue_retry_payment(self):
        for task in self:
            invoice = task.invoice_id
            partner = invoice.partner_id

            payments = invoice.payment_ids.filtered(lambda p: p.state == "posted")
            if payments:
                token = payments.sorted("id")[-1].partner_id.payment_token_id
            else:
                token = partner.payment_token_id

            if not token:
                raise UserError(
                    _("Invoice id %d: could not find a payment token!") % invoice.id
                )

            _logger.info(
                "Task %s: retrying payment of invoice %s of %s with %s",
                task.id,
                invoice.name,
                partner.name,
                token.payment_details,
            )

            (
                self.env["account.payment.register"]
                .with_context(
                    active_model="account.move",
                    active_ids=invoice.ids,
                    slimpay_payin_label=self.slimpay_payment_label,
                )
                .create(
                    {
                        "journal_id": invoice.payment_mode_id.fixed_journal_id.id,
                        "payment_token_id": token.id,
                    }
                )
                ._create_payments()
            )

    @api.model
    def _slimpay_payment_issue_handle(self, project, client, issue_doc):
        task = self._slimpay_payment_issue_get_or_create(project, client, issue_doc)
        invoice = task.invoice_id

        if issue_doc.get("rejectReason"):
            msg = _("Reject reason is %(code)s: %(text)s")
            code = issue_doc.get("rejectReasonCode", "")
            if code in SLIMPAY_ERROR_CODES:
                text = _(SLIMPAY_ERROR_CODES[code])
            else:
                text = _("Unknown reject error")

            task.message_post(body=msg % {"code": code, "text": text})

        if not task.slimpay_payment_issue_process_automatically():
            task.update(
                {"stage_id": self.env.ref("payment_slimpay_issue.stage_orphan").id}
            )
            return

        task.invoice_unpaid_count += 1

        _logger.info('Unreconciling invoice "%s"', invoice.name)
        invoice.payment_move_line_ids.remove_move_reconcile()
        _logger.info('Invoice payments "%s"', invoice.payment_ids.ids)
        for payment in invoice.payment_ids:
            _logger.info('Canceling payment "%s"', payment.id)
            payment.cancel()

        rejected_amount = float(issue_doc["rejectAmount"])
        if invoice.amount_total < rejected_amount:
            fees = rejected_amount - invoice.amount_total
            self._slimpay_payment_issue_invoice_fees(invoice, "bank", fees)
            self._slimpay_payment_issue_create_supplier_invoice_fees(
                "%s-REJ%d" % (invoice.name, task.invoice_unpaid_count),
                reject_date(issue_doc),
                fees,
            )

        if (
            task.invoice_unpaid_count
            > self._slimpay_payment_issue_management_fees_retrial_num()
        ):
            self._slimpay_payment_issue_invoice_fees(invoice, "management")

        if task.invoice_unpaid_count > self._slimpay_payment_max_retrials():
            task.update(
                {
                    "stage_id": self.env.ref(
                        "payment_slimpay_issue.stage_max_trials_reached"
                    ).id
                }
            )
        else:
            task.update(
                {
                    "stage_id": self.env.ref(
                        "payment_slimpay_issue.stage_warn_partner_and_wait"
                    ).id
                }
            )
        return task

    def _slimpay_payment_issue_send_sms(self):
        country_code = self.partner_id.country_id.code
        phone = normalize_phone(
            self.partner_id.get_mobile_phone(),
            country_code,
        )
        if phone:
            template = self.env.ref("payment_slimpay_issue.sms")
            self.with_delay().send_sms_from_template(
                template,
                self,
                sms_numbers=[phone],
            )
        else:
            _logger.warning(
                "Could not send SMS to %s (id %s): no phone number found"
                % (self.partner_id.name, self.partner_id.id)
            )

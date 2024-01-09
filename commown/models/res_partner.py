import logging
from base64 import b64decode
from datetime import date

import magic

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)


_PROPERTY_ACCOUNT_DATA = {
    "payable": {
        "account_type": "account.data_account_type_payable",
        "field_name": "property_account_payable_id",
        "code_template": "401-F-%d",
        "ref_account": "l10n_fr.1_fr_pcg_pay",
    },
    "receivable": {
        "account_type": "account.data_account_type_receivable",
        "field_name": "property_account_receivable_id",
        "code_template": "411-C-%d",
        "ref_account": "l10n_fr.1_fr_pcg_recv",
    },
}

_PAYMENT_PREF_FIELDS = {
    "invoice_merge_next_date",
    "invoice_merge_recurring_rule_type",
    "invoice_merge_recurring_interval",
}

_PAYMENT_FIELDS = _PAYMENT_PREF_FIELDS | {"payment_token_id"}

_SYNC_CTX = "partner_payment_fields_sync"


class FileTooBig(Exception):
    def __init__(self, field, msg):
        self.field = field
        self.msg = msg


class CommownPartner(models.Model):
    _inherit = "res.partner"

    auto_widget_binary_fields = [
        "id_card1",
        "id_card2",
        "proof_of_address",
        "company_record",
    ]

    max_doc_image_size = (1240, 1754)
    max_doc_size_Mo = 5

    _binary_field_policy = (
        "Images are resized to %dx%d and, all files are limited to %dMo."
        % (max_doc_image_size + (max_doc_size_Mo,))
    )

    id_card1 = fields.Binary(
        "ID card",
        attachment=True,
        store=True,
        help=("This field holds a file to store the ID card. " + _binary_field_policy),
    )

    id_card2 = fields.Binary(
        "ID card (2)",
        attachment=True,
        store=True,
        help=(
            "This field holds a file to store the ID card (2). " + _binary_field_policy
        ),
    )

    proof_of_address = fields.Binary(
        "Proof of address",
        attachment=True,
        store=True,
        help=(
            "This field holds a file to store a proof of address. "
            + _binary_field_policy
        ),
    )

    company_record = fields.Binary(
        "Company record",
        attachment=True,
        store=True,
        help=(
            "This field holds a file to store a company record. " + _binary_field_policy
        ),
    )

    def _default_country(self):
        return self.env["res.company"]._company_default_get().country_id

    country_id = fields.Many2one(default=_default_country)

    def _apply_bin_field_size_policy(self, vals):
        """Apply the binary field limit policy: resize images, raise if the
        final value is still too big.
        """
        for field in self.auto_widget_binary_fields:
            posted_value = vals.get(field)
            if posted_value:
                if isinstance(posted_value, str):
                    b64value = posted_value.encode("ascii")
                elif isinstance(posted_value, bytes):
                    b64value = posted_value
                else:
                    raise ValueError(
                        "The type %s is not covered by this function"
                        % type(posted_value)
                    )
                value = b64decode(b64value)
                if magic.from_buffer(value, mime=True).startswith("image"):
                    vals[field] = tools.image_resize_image(
                        b64value, avoid_if_small=True, size=self.max_doc_image_size
                    )
                    value = b64decode(vals[field])
                if len(value) > 1024 * 1024 * self.max_doc_size_Mo:
                    raise FileTooBig(
                        field, _("File too big (limit is %dMo)") % self.max_doc_size_Mo
                    )

    def _create_property_account(self, property_name):
        """If partner's payable or receivable account does not exist or
        is the fr standard one, create a dedicated account for the partner.
        The account is associated to the commercial_partner, if any, but
        linked to both partners.
        """
        assert property_name in ("payable", "receivable")

        tva = self.env.ref("l10n_fr.1_tva_normale")
        tag = self.env.ref("account.account_tag_operating")

        data = _PROPERTY_ACCOUNT_DATA[property_name]

        for partner in self:
            partner = partner.commercial_partner_id

            account = getattr(partner, data["field_name"])
            if not account or account == self.env.ref(data["ref_account"]):
                new_account = self.env["account.account"].create(
                    {
                        "code": data["code_template"] % partner.id,
                        "name": partner.name,
                        "tag_ids": [(6, 0, tag.ids)],
                        "user_type_id": self.env.ref(data["account_type"]).id,
                        "tax_ids": [(6, 0, tva.ids)],
                        "reconcile": True,
                    }
                )
                (partner | partner.child_ids).update({data["field_name"]: new_account})

    def _create_payable_account(self):
        "See _create_property_account doc string"
        self._create_property_account("payable")

    def _create_receivable_account(self):
        "See _create_property_account doc string"
        # Protect against double creation
        partner = self.commercial_partner_id
        code = _PROPERTY_ACCOUNT_DATA["receivable"]["code_template"] % partner.id
        existing = self.env["account.account"].search([("code", "=", code)])
        if existing:
            (partner | partner.child_ids).update(
                {"property_account_receivable_id": existing.id},
            )
        self._create_property_account("receivable")

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        self._apply_bin_field_size_policy(vals)
        result = super(CommownPartner, self).create(vals)

        if result.type == "invoice" and result.parent_id:
            result.parent_id._copy_payment_fields_to_invoice_children()

        if result.supplier:
            result._create_payable_account()

        return result

    def _copy_payment_fields_to_invoice_children(self):
        self.ensure_one()

        if self._context.get(_SYNC_CTX, False):
            return

        _msg = "Syncing payment fields from partner %s (id %d) to its child %s (id %d)"
        _self = self.with_context(**{_SYNC_CTX: True})
        for p_inv in _self.child_ids.filtered(lambda p: p.type == "invoice"):
            _logger.debug(_msg, self.name, self.id, p_inv.name, p_inv.id)
            p_inv.update({f: self[f] for f in _PAYMENT_FIELDS})

    @api.multi
    def write(self, vals):
        self._apply_bin_field_size_policy(vals)

        if "parent_id" in vals:
            old_recv_acc = self.property_account_receivable_id

        result = super(CommownPartner, self).write(vals)

        if _PAYMENT_FIELDS.intersection(vals):
            # Sync payment fields to invoice childs:
            self._copy_payment_fields_to_invoice_children()

            # If not updating because of above sync, update parent payment fields:
            if self.type == "invoice" and not self._context.get(_SYNC_CTX, False):
                debug_msg = (
                    "Syncing payment fields from partner %s (id %d) to"
                    " its parent %s (id %d)"
                )
                p_parent = self.parent_id
                _logger.debug(debug_msg, self.name, self.id, p_parent.name, p_parent.id)
                p_parent.update({f: self[f] for f in _PAYMENT_FIELDS})

        if "supplier" in vals and vals["supplier"]:
            self._create_payable_account()

        if "parent_id" in vals and old_recv_acc:
            data = _PROPERTY_ACCOUNT_DATA["receivable"]
            ref_account = self.env.ref(data["ref_account"])
            if (
                old_recv_acc != ref_account
                and self.parent_id.property_account_receivable_id == ref_account
            ):
                self.parent_id.property_account_receivable_id = old_recv_acc.id
                old_recv_acc.update(
                    {
                        "code": data["code_template"] % self.parent_id.id,
                        "name": self.parent_id.name,
                    }
                )

        return result

    @api.model
    def signup_retrieve_info(self, token):
        """Override auth_signup method for compat with partner_firstname:
        retrieve first- and last- name for the reset password form.
        """
        partner = self._signup_retrieve_partner(token, raise_exception=True)
        res = {"db": self.env.cr.dbname}
        if partner.signup_valid:
            res["token"] = token
            res["firstname"] = partner.firstname
            res["lastname"] = partner.lastname
        if partner.user_ids:
            res["login"] = partner.user_ids[0].login
        else:
            res["email"] = res["login"] = partner.email or ""
        return res

    def reset_payment_token(self):
        "Force the reset on payment preferences on payment token reset"
        super().reset_payment_token()
        self.update({f: False for f in _PAYMENT_PREF_FIELDS})

    @api.multi
    def action_set_as_invoice_recipient(self):
        self.ensure_one()

        contracts = self.env["contract.contract"].search(
            [
                ("invoice_partner_id", "=", self.parent_id.id),
                "|",
                ("date_end", ">=", date.today()),
                "&",
                ("date_end", "=", False),
                ("recurring_next_date", "!=", False),
            ]
        )
        contracts.update({"invoice_partner_id": self.id})

        invoices = self.env["account.invoice"].search(
            [
                ("type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("partner_id", "=", self.parent_id.id),
                ("invoice_line_ids.contract_line_id", "!=", False),
            ]
        )
        invoices.update({"partner_id": self.id})

        msg = _("Modified %d contracts and %d invoices") % (
            len(contracts),
            len(invoices),
        )
        self.env.user.notify_success(message=msg, title=_("Information"), sticky=True)
        return True

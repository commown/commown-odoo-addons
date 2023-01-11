import logging
from base64 import b64decode

import magic

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)


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
            b64value = vals.get(field)
            if b64value:
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

    def _create_payable_account(self):
        """If partner is a supplier and its payable account does not exist or
        is the fr standard one, create a payable account dedicated to
        this supplier. For employees of a company, go up the parent_id
        hierarchy and create the account there.
        """

        ref_account = self.env.ref("l10n_fr.1_fr_pcg_pay")
        tva = self.env.ref("l10n_fr.1_tva_normale")
        tag = self.env.ref("account.account_tag_operating")
        account_type = self.env.ref("account.data_account_type_payable")
        account_model = self.env["account.account"]

        for partner in self:
            partner = partner.commercial_partner_id

            account = partner.property_account_payable_id
            if not account or account == ref_account:
                new_account = account_model.create(
                    {
                        "code": "401-F-%s" % partner.id,
                        "name": partner.name,
                        "tag_ids": [(6, 0, tag.ids)],
                        "user_type_id": account_type.id,
                        "tax_ids": [(6, 0, tva.ids)],
                        "reconcile": True,
                    }
                )
                (partner | partner.child_ids).update(
                    {"property_account_payable_id": new_account}
                )

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        self._apply_bin_field_size_policy(vals)
        result = super(CommownPartner, self).create(vals)
        if result.supplier:
            result._create_payable_account()
        return result

    def write(self, vals, **kwargs):
        self._apply_bin_field_size_policy(vals)
        result = super(CommownPartner, self).write(vals, **kwargs)
        if "supplier" in vals and vals["supplier"]:
            self._create_payable_account()
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

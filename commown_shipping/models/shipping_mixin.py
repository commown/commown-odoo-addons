import json
import logging
import os
import re
import sys
from base64 import b64encode
from subprocess import CalledProcessError, run as _run
from tempfile import gettempdir, mktemp

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .colissimo_utils import AddressTooLong, ColissimoError

REF_FROM_NAME_RE = re.compile(r".*\[(?P<ref>[^\]]+)\].*")

_logger = logging.getLogger(__name__)


# 3.6 compat for subprocess.run (3.6 is used by the CI)
if tuple(sys.version_info)[:2] < (3, 7):
    # subprocess.run as no capture_output kwarg, so drop it
    def run(*args, **kwargs):
        kwargs.pop("capture_output")
        return _run(*args, **kwargs)

else:
    run = _run


def _ref_from_name(name):
    match = REF_FROM_NAME_RE.match(name)
    return match.groupdict()["ref"] if match else ""


class CommownShippingMixin(models.AbstractModel):
    _name = "commown.shipping.mixin"

    # Needs to be overloaded: used to store multiple label pdfs
    # (when printing several labels at once)
    _shipping_parent_rel = None
    _description = "Object used to edit shipping labels and track parcels"

    @api.multi
    def _shipping_parent(self):
        return self.mapped(self._shipping_parent_rel)

    @api.multi
    def _default_shipping_account(self):
        return self._shipping_parent().mapped("shipping_account_id")

    @api.multi
    def _create_parcel_label(self, parcel, shipping_account, recipient, ref):
        """Generate a new label from following arguments:
        - parcel: a commown.parcel.type entity
        - shipping_account: Shipping Account for colissimo
        - recipient: the recipient res.partner entity
        - ref: a string reference to be printed on the parcel
        """
        self.ensure_one()

        meta_data, label_data = parcel.colissimo_label(
            shipping_account.account,
            shipping_account.password,
            parcel.sender,
            recipient,
            ref,
        )

        if meta_data and not label_data:
            raise ValueError(json.dumps(meta_data))
        assert meta_data and label_data

        return self._attachment_from_label(parcel.name + ".pdf", meta_data, label_data)

    @api.multi
    def _attachment_from_label(self, name, meta_data, label_data):
        return self.env["ir.attachment"].create(
            {
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
                "datas": b64encode(label_data),
                "datas_fname": meta_data["labelResponse"]["parcelNumber"] + ".pdf",
                "name": name,
                "public": False,
                "type": "binary",
            }
        )

    @api.multi
    def label_attachment(self, parcel):
        self.ensure_one()
        domain = [
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("name", "=", parcel.name + ".pdf"),
        ]
        return self.env["ir.attachment"].search(domain)

    @api.multi
    def _get_or_create_label(self, parcel, *args, **kwargs):
        "Return current label if expedition_ref is set, or create a new one"
        self.ensure_one()
        return self.label_attachment(parcel) or self._create_parcel_label(
            parcel, *args, **kwargs
        )

    @api.multi
    def get_label_ref(self):
        self.ensure_one()
        entity_ref = _ref_from_name(self.name)
        if entity_ref:
            return entity_ref
        else:
            entity_ref = str(self.id)
            parent = self._shipping_parent()
            parent_ref = _ref_from_name(parent.name) or str(parent.id)
            return "{}-{}".format(parent_ref, entity_ref)

    @api.multi
    def _print_parcel_labels(self, parcel, account=None, force_single=False):
        paths = []

        for record in self:
            account = record._default_shipping_account()
            try:
                label = record._get_or_create_label(
                    parcel, account, record.partner_id, record.get_label_ref()
                )
            except ColissimoError as exc:
                msg = _("Colissimo error:\n%s") % exc.args[0]
                raise UserError(msg)
            except AddressTooLong as exc:
                msg = _('Address too long for "%s"')
                raise UserError(msg % exc.partner.name)
            if len(self) == 1 and force_single:
                return label
            paths.append(label._full_path(label.store_fname))

        fpath = os.path.join(gettempdir(), mktemp(suffix=".pdf"))
        result_path = None
        try:
            run(
                ["pdftk"] + paths + ["cat", "output", fpath],
                capture_output=True,
                check=True,
            )
            run(
                [
                    "pdfjam",
                    "--nup",
                    "2x2",
                    "--offset",
                    "0.1cm 2.4cm",
                    "--trim",
                    "1.95cm 5.8cm 17.4cm 2.5cm",
                    "--clip",
                    "true",
                    "--frame",
                    "false",
                    "--scale",
                    "0.98",
                    "--outfile",
                    gettempdir(),
                    fpath,
                ],
                capture_output=True,
                check=True,
            )
            result_path = fpath[:-4] + "-pdfjam" + fpath[-4:]

        except CalledProcessError as exc:
            msg = exc.stderr.decode("utf-8") if exc.stderr else "No err output"
            _logger.exception("PDF concatenation or assembly failed:\n%s", msg)
            fpath = None
            raise

        else:
            with open(result_path, "rb") as fobj:
                data = b64encode(fobj.read())
            parent = self[0]._shipping_parent()
            attrs = {
                "res_model": parent._name,
                "res_id": parent.id,
                "name": parcel.name + ".pdf",
            }
            domain = [(k, "=", v) for k, v in list(attrs.items())]
            for att in self.env["ir.attachment"].search(domain):
                att.unlink()
            attrs.update(
                {
                    "mimetype": "application/pdf",
                    "datas": data,
                    "datas_fname": "colissimo.pdf",
                    "public": False,
                    "type": "binary",
                }
            )
            return self.env["ir.attachment"].create(attrs)

        finally:
            for p in (fpath, result_path):
                if p is None:
                    continue
                try:
                    os.unlink(p)
                except BaseException:
                    _logger.error("Could not remove tmp label file %r", p)

    @api.multi
    def parcel_labels(self, parcel_name, force_single=False):

        parcel = (
            self.env["commown.parcel.type"]
            .search([("technical_name", "=", parcel_name)])
            .ensure_one()
        )

        return self._print_parcel_labels(parcel, force_single=force_single)


class CommownShippingParentMixin(models.AbstractModel):
    _name = "commown.shipping.parent.mixin"
    _description = "Object that contains shipping objects"

    shipping_account_id = fields.Many2one(
        "commown.shipping_account", string="Shipping account"
    )

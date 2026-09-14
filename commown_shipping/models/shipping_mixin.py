import re

from odoo import fields, models

REF_FROM_NAME_RE = re.compile(r".*\[(?P<ref>[^\]]+)\].*")


def _ref_from_name(name):
    match = REF_FROM_NAME_RE.match(name)
    return match.groupdict()["ref"] if match else ""


class CommownShippingMixin(models.AbstractModel):
    _name = "commown.shipping.mixin"
    _description = "Object used to edit shipping labels"

    recipient_partner_id = fields.Many2one(
        "res.partner",
        "Delivery partner",
        domain="[('commercial_partner_id', '=', commercial_partner_id)]",
        help=(
            "If left empty, a delivery partner will be looked-up for specified"
            " partner:\n"
            "- for crm leads, the sale's delivery partner will be used;\n"
            "- for project tasks (support, etc.), odoo will try to find a"
            " delivery partner from the partner or its company."
        ),
    )

    # Needs to be overloaded
    _shipping_parent_rel = None

    def _shipping_parent(self):
        return self.mapped(self._shipping_parent_rel)

    def get_label_ref(self):
        self.ensure_one()
        entity_ref = _ref_from_name(self.name)
        if entity_ref:
            return entity_ref
        else:
            entity_ref = str(self.id)
            parent = self._shipping_parent()
            parent_ref = _ref_from_name(parent.name) or str(parent.id)
            return f"{parent_ref}-{entity_ref}"

    def _delivery_typed_partner(self):
        "If current partner has a delivery-typed address return it else return None"
        delivery_partner = self.env["res.partner"].browse(
            self.partner_id.address_get(["delivery"])["delivery"]
        )
        if delivery_partner.type == "delivery":
            return delivery_partner

    def _recipient_partner(self):
        "Give the opportunity to override shipping recipient computation"
        self.ensure_one()
        return (
            self.recipient_partner_id
            or self._delivery_typed_partner()
            or self.partner_id
        )

import re

from odoo import models

REF_FROM_NAME_RE = re.compile(r".*\[(?P<ref>[^\]]+)\].*")


def _ref_from_name(name):
    match = REF_FROM_NAME_RE.match(name)
    return match.groupdict()["ref"] if match else ""


class CommownShippingMixin(models.AbstractModel):
    _name = "commown.shipping.mixin"
    _description = "Object used to edit shipping labels"

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

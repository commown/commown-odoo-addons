from odoo import models


class Contract(models.Model):
    _inherit = "contract.contract"

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(Contract, record).name_get()[0]
            if record.contract_template_id:
                name += " (%s)" % record.contract_template_id.name
            result.append((record.id, name))
        return result

    def amount(self):
        """Compute the sum of contract line price that have no formula or a
        formula marked with '[DE]' (for 'commitment duration' in french).
        """
        self.ensure_one()
        return sum(
            self.contract_line_ids.filtered(
                lambda l: (l.qty_type != "variable" or "[DE]" in l.qty_formula_id.name)
            ).mapped("price_subtotal")
        )

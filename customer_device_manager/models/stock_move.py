from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _set_lot_contract(self, lots, contract, **kwargs):
        "Create Device Assignment on device expedition validation"
        super()._set_lot_contract(lots, contract, **kwargs)

        partner = contract.partner_id.commercial_partner_id
        if partner.is_company:
            assign_model = self.env["customer_device_manager.device_assignment"]
            hist_model = self.env["customer_device_manager.device_assignment_history"]
            for lot in lots:
                self.env["customer_device_manager.device_assignment"].create(
                    {
                        "device_id": lot.id,
                        "partner_id": partner.id,
                        "assignment_date": fields.Datetime.now(),
                    }
                )

    def _unset_lot_contract(self, lots, contract, location_dest, **kwargs):
        "Archive Device Assignment on device return validation"
        super()._unset_lot_contract(lots, contract, location_dest, **kwargs)

        partner = contract.partner_id.commercial_partner_id
        assignments = self.env["customer_device_manager.device_assignment"].search(
            [
                ("device_id", "in", lots.ids),
                ("partner_id", "child_of", partner.id),
                ("device_location", "=", "at_customer"),
            ]
        )
        assignments.update({"device_location": "at_commown"})

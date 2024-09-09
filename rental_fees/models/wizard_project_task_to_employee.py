from odoo import _, api, models


class ProjectTaskDeviceToEmployeeWizard(models.TransientModel):
    _inherit = "project.task.to.employee.wizard"

    @api.multi
    def execute(self):
        super().execute()
        lot = self.lot_id
        fees_def = self.env["rental_fees.definition"].search(
            [
                ("order_ids.order_line.move_ids.move_line_ids.lot_id", "=", lot.id),
                ("product_template_id", "=", lot.product_id.product_tmpl_id.id),
            ]
        )

        if fees_def:
            assert len(fees_def) == 1, _("More than 1 fees def found for %s") % lot.name
            if lot in fees_def.excluded_devices.mapped("device"):
                info = _(
                    "Device %(serial)s was already excluded from fees"
                    " (in fees def id %(def_id)d)"
                )
            else:
                info = _("Device %(serial)s excluded from fees in def id %(def_id)d")
                context = {"lang": fees_def.partner_id.lang}  # Use fees partner lang
                reason = _("Device used by employee %s")
                self.env["rental_fees.excluded_device"].create(
                    {
                        "fees_definition_id": fees_def.id,
                        "device": lot.id,
                        "reason": reason % self.task_id.partner_id.firstname,
                    },
                )

            self.env.user.notify_info(
                info % {"serial": lot.name, "def_id": fees_def.id}
            )

        else:
            self.env.user.notify_info(
                "Device %s is not subject to fees as of now." % lot.name
            )

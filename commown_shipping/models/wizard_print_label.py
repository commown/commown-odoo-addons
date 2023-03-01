from odoo import api, fields, models


class ProjectTaskAbstractPrintLabelWizard(models.AbstractModel):
    _name = "commown_shipping.abstract_print_label.wizard"
    _description = "Print a Colissimo label (abstract class)"

    shipping_ids = None  # Override me!

    parcel_type_id = fields.Many2one(
        "commown.parcel.type",
        string="Parcel type",
        required=True,
    )

    use_full_page_per_label = fields.Boolean(
        string="Use a full page per label",
        default=False,
    )

    @api.multi
    def print_label(self):
        label = self.shipping_ids.parcel_labels(
            self.parcel_type_id.technical_name,
            force_single=self.use_full_page_per_label,
        )

        return {
            "type": "ir.actions.act_multi",
            "actions": [
                {
                    "type": "ir.actions.act_url",
                    "url": label.website_url,
                    "target": "current",
                },
                {"type": "ir.actions.act_window_close"},
                {"type": "ir.actions.act_view_reload"},
            ],
        }


class ProjectTaskPrintLabelWizard(models.TransientModel):
    _name = "commown_shipping.task.print_label.wizard"
    _description = "Print a Colissimo label from a project task"
    _inherit = "commown_shipping.abstract_print_label.wizard"

    shipping_ids = fields.Many2many(
        comodel_name="project.task",
        string="Tasks",
    )


class CrmLeadPrintLabelWizard(models.TransientModel):
    _name = "commown_shipping.lead.print_label.wizard"
    _description = "Print a Colissimo label from a crm lead"
    _inherit = "commown_shipping.abstract_print_label.wizard"

    shipping_ids = fields.Many2many(
        comodel_name="crm.lead",
        string="Leads",
    )

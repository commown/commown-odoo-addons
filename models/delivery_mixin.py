from odoo import api, models, fields


class CommownTrackDeliveryMixin(models.AbstractModel):
    _name = "commown.track_delivery.mixin"
    _inherit = "commown.shipping.mixin"

    expedition_ref = fields.Text("Expedition reference", size=64)
    expedition_date = fields.Date("Expedition Date")
    expedition_status = fields.Text("Expedition status", size=256)
    expedition_status_fetch_date = fields.Datetime(
        "Expedition status fetch date")
    expedition_urgency_mail_sent = fields.Boolean(
        "Expedition urgency mail send", default=False)
    delivery_date = fields.Date("Delivery Date")

    # Need to be overloaded
    _delivery_tracking_parent_rel = None
    _delivery_stage_type = None

    @api.multi
    def _delivery_tracking_parent(self):
        return self.mapped(self._delivery_tracking_parent_rel)

    def _default_perform_actions_on_delivery(self):
        parent = self._delivery_tracking_parent()
        if not parent:
            context = self.env.context
            default_rel = "default_%s" % self._delivery_tracking_parent_rel
            if default_rel in context:
                parent = self.env[parent._name].browse(context[default_rel])
        return parent.default_perform_actions_on_delivery if parent else True

    start_contract_on_delivery = fields.Boolean(
        default=_default_perform_actions_on_delivery,
        string='Automatic contract start on delivery')
    send_email_on_delivery = fields.Boolean(
        default=_default_perform_actions_on_delivery,
        string='Automatic email on delivery')
    on_delivery_email_template_id = fields.Many2one(
        'mail.template', string='Custom email model for this entity')

    @api.multi
    def delivery_email_template(self):
        """ If current entity is attached to a parent with shipping activated,
        return the entity's custom delivery mail template if any or the parent's
        delivery mail template if any. Return None if all other cases.
        """
        self.ensure_one()
        parent = self._delivery_tracking_parent()
        return parent and parent.used_for_shipping and (
            self.on_delivery_email_template_id
            or parent.on_delivery_email_template_id
            ) or None


class CommownDeliveryParentMixin(models.AbstractModel):
    _name = 'commown.delivery.parent.mixin'

    default_perform_actions_on_delivery = fields.Boolean(
        'By default, perform actions on delivery',
        default=True)
    on_delivery_email_template_id = fields.Many2one(
        'mail.template', string='Default delivery email model for this entity')

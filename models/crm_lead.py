from datetime import datetime

from odoo import models, fields, api


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'commown.shipping.mixin']

    _shipping_parent_rel = 'team_id'

    def _default_perform_actions_on_delivery(self):
        team = self.team_id
        if not team:
            context = self.env.context
            if "default_team_id" in context:
                team = self.env["crm.team"].browse(context["default_team_id"])
        return team.default_perform_actions_on_delivery if team else True

    expedition_ref = fields.Text("Expedition reference", size=64)
    expedition_date = fields.Date("Expedition Date")
    expedition_status = fields.Text("Expedition status", size=256)
    expedition_status_fetch_date = fields.Datetime(
        "Expedition status fetch date")
    expedition_urgency_mail_sent = fields.Boolean(
        "Expedition urgency mail send", default=False)
    delivery_date = fields.Date("Delivery Date")
    start_contract_on_delivery = fields.Boolean(
        default=_default_perform_actions_on_delivery,
        string='Automatic contract start on delivery')
    send_email_on_delivery = fields.Boolean(
        default=_default_perform_actions_on_delivery,
        string='Automatic email on delivery')
    on_delivery_email_template_id = fields.Many2one(
        'mail.template', string='Custom email model for this lead')
    so_line_id = fields.Many2one('sale.order.line', 'Ligne de commande')
    used_for_shipping = fields.Boolean(
        'Used for shipping', related='team_id.used_for_shipping')

    @api.multi
    def delivery_email_template(self):
        """ If current lead is attached to a team with shipping activated,
        return the lead's custom delivery mail template if any or the team's
        delivery mail template if any. Return None if all other cases.
        """
        self.ensure_one()
        return self.team_id and self.team_id.used_for_shipping and (
            self.on_delivery_email_template_id
            or self.team_id.on_delivery_email_template_id
            ) or None

    @api.multi
    def _default_shipping_parcel_type(self):
        return self.mapped('so_line_id.product_id.shipping_parcel_type_id')

    @api.multi
    def _attachment_from_label(self, name, meta_data, label_data):
        self.update({
            'expedition_ref': meta_data['labelResponse']['parcelNumber'],
            'expedition_date': datetime.today(),
            'delivery_date': False  ,
        })
        return super(CrmLead, self)._attachment_from_label(
            name, meta_data, label_data)


    @api.multi
    def parcel_labels(self, parcel_name=None, force_single=False):

        if parcel_name is not None:
            return super(CrmLead, self).parcel_labels(
                parcel_name, force_single=force_single)
        else:
            return self._print_parcel_labels(
                self._default_shipping_parcel_type(),
                force_single=force_single)

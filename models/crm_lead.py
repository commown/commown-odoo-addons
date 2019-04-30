from odoo import models, fields, api


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'commown.shipping.mixin']

    _shipping_parent_rel = 'team_id'

    expedition_ref = fields.Text("Expedition reference", size=64)
    expedition_date = fields.Date("Expedition Date")
    expedition_status = fields.Text("Expedition status", size=256)
    expedition_status_fetch_date = fields.Datetime(
        "Expedition status fetch date")
    expedition_urgency_mail_sent = fields.Boolean(
        "Expedition urgency mail send", default=False)
    delivery_date = fields.Date("Delivery Date")
    start_contract_on_delivery = fields.Boolean(
        default=True, string='Automatic contract start on delivery')
    send_email_on_delivery = fields.Boolean(
        default=True, string='Automatic email on delivery')
    on_delivery_email_template_id = fields.Many2one(
        'mail.template', string='Custom email model for this lead')
    so_line_id = fields.Many2one('sale.order.line', 'Ligne de commande')

    @api.multi
    def _default_shipping_parcel_type(self):
        return self.mapped('so_line_id.product_id.shipping_parcel_type_id')

    @api.multi
    def parcel_labels(self, parcel_name=None, force_single=False):

        if parcel_name is not None:
            return super(CrmLead, self).parcel_labels(
                parcel_name, force_single=force_single)
        else:
            return self._print_parcel_labels(
                self._default_shipping_parcel_type(),
                force_single=force_single)

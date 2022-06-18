from odoo import api, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def urban_mine_send_label(self, label_name):
        # Send the message as the user of the lead
        if self.user_id:
            self = self.sudo(self.user_id)

        label = self.parcel_labels(label_name, force_single=True)
        email_template = self.env.ref("urban_mine.email_template_with_label").id

        self.message_post_with_template(
            email_template, attachment_ids=[(4, label.id)],
        )

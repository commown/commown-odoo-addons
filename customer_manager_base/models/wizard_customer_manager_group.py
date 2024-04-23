from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class WizardCustomerManagerGroup(models.TransientModel):
    _name = "customer_manager_base.customer_group_wizard"
    _description = "Wizard to add portal users to customer-dedicated groups"

    partner_id = fields.Many2one("res.partner", required=True)
    in_group_accounting = fields.Boolean()
    in_group_purchase = fields.Boolean()
    in_group_it_support = fields.Boolean()
    in_group_contract_manager = fields.Boolean()

    @api.onchange("partner_id")
    def _compute_in_group(self):
        user = self._get_user()
        for group, field_name in self._group_field_dict().items():
            setattr(self, field_name, user in group.users)

    def _get_user(self):
        "Return the portal user related to related partner or raise a UserError"

        user = self.partner_id.user_ids and self.partner_id.user_ids[0]
        if not user or user not in self.env.ref("base.group_portal").users:
            raise UserError(_("Partner has no portal access!"))
        return user

    def _group_field_dict(self):
        "Return a dict of the form {group: field name}"

        prefix = "in_group_"
        result = {}

        for field_name in self._fields:
            if field_name.startswith("in_group_"):
                _ref = field_name[len(prefix) :]
                group = self.env.ref("customer_manager_base.group_customer_%s" % _ref)
                result[group] = field_name

        return result

    def execute(self):
        "Add or remove user from the groups"
        if not self.env.user in self.env.ref("sales_team.group_sale_manager").users:
            raise AccessError(_("You are not allowed to execute this operation"))
        user = self._get_user()
        for group, field_name in self._group_field_dict().items():
            if getattr(self, field_name):
                group.sudo().users |= user
            else:
                group.sudo().users -= user

import base64

from odoo import _, api, fields, models, tools
from odoo.modules import get_module_resource


class Employee(models.Model):
    _name = "customer_team_manager.employee"
    _inherit = "customer_team_manager.customer_company_object"
    _description = "An employee of a customer"

    firstname = fields.Char(
        string="First name",
        required=True,
    )

    lastname = fields.Char(
        string="Last name",
        required=True,
    )

    email = fields.Char(
        required=True,
    )

    phone = fields.Char()

    partner = fields.Many2one(
        "res.partner",
        string="Partner",
        groups="sales_team.group_sale_manager",
        index=True,
        copy=False,
    )

    team = fields.Many2one(
        "customer_team_manager.team",
        index=True,
        ondelete="restrict",
    )

    active = fields.Boolean(default=True)

    portal_status = fields.Selection(
        [
            ("not_granted", "Not granted"),
            ("never_connected", "Never connected"),
            ("already_connected", "Already connected"),
        ],
        default="not_granted",
        string="Portal status",
        compute="_compute_portal_status",
        store=False,
    )

    image_medium = fields.Binary(
        "Medium-sized image",
        attachment=True,
        default=lambda self: self._compute_default_image(),
        help="Medium-sized image of this employee. It is automatically "
        "resized as a 128x128px image, with aspect ratio preserved.",
    )

    def _compute_default_image(self):
        img_path = get_module_resource("base", "static/img", "avatar.png")
        with open(img_path, "rb") as f:
            image = f.read()
        image = tools.image_colorize(image)
        return base64.b64encode(image)

    def _compute_portal_status(self):
        for _rec in self:

            result = "not_granted"

            rec = _rec.sudo()
            if rec.partner and rec.partner.user_ids:
                user = rec.partner.user_ids[0]
                if user.active and user.has_group("base.group_portal"):
                    if user.state == "active":
                        result = "already_connected"
                    else:
                        result = "never_connected"

            _rec.portal_status = result

    @api.onchange("company")
    def _onchange_company_set_partner_domain(self):
        if self.env.user.has_group("sales_team.group_sale_manager"):
            return {
                "domain": {
                    "partner": [
                        ("is_company", "=", False),
                        ("commercial_partner_id", "=", self.company.id),
                    ]
                }
            }

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.firstname + " " + record.lastname))
        return result

    @api.onchange("partner")
    def _onchange_partner_set_attributes(self):
        if not self.partner:
            return

        warnings = []

        for fieldname in ("firstname", "lastname", "phone", "email"):
            if self[fieldname] != self.partner[fieldname]:
                if self[fieldname]:
                    warnings.append(fieldname)
                self[fieldname] = self.partner[fieldname]

        if warnings:
            msg = _("Following field values were overriden:<br>- %s")
            fields = self.partner.fields_get()
            self.env.user.notify_warning(
                sticky=True,
                message=msg % "<br>- ".join(fields[f]["string"] for f in warnings),
            )

    def prepare_portal_wizard(self, in_portal):
        "Return the configured wizard. May be overriden by another module."

        partner_id = self.sudo().partner.id
        model = self.env["portal.wizard"].with_context(active_ids=[partner_id])
        portal_wizard = model.sudo().create({})
        portal_wizard.user_ids.update({"in_portal": in_portal})
        return portal_wizard

    def set_portal_access(self, in_portal):
        "Use portal wizard to grant or remove portal access according to in_portal"
        self.ensure_one()
        wizard = self.prepare_portal_wizard(in_portal)
        wizard.action_apply()

    @api.multi
    def action_grant_portal_access(self):
        self.set_portal_access(True)

    @api.multi
    def action_revoke_portal_access(self):
        self.set_portal_access(False)

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        "Automatically create res.partner res.users instances if needed"

        if vals.get("partner"):
            partner = self.env["res.partner"].browse(vals["partner"])
            # Email is readonly in the UI when partner has an active user, so set now:
            vals["email"] = partner.email

        if not vals.get("image_medium"):
            vals["image_medium"] = self._compute_default_image()
        elif isinstance(vals["image_medium"], str):
            # This is the case in v12 when creating an employee from scratch
            vals["image_medium"] = bytes(vals["image_medium"], "ascii")
        vals["image_medium"] = tools.image_resize_image_medium(vals["image_medium"])

        result = super().create(vals)
        partner = result.sudo().partner

        if not partner:
            result.sudo().partner = (
                self.env["res.partner"]
                .sudo()
                .create(
                    {
                        "firstname": result.firstname,
                        "lastname": result.lastname,
                        "email": result.email,
                        "phone": result.phone,
                        "parent_id": result.sudo().company.id,
                    }
                )
            )

        return result

    @api.multi
    def write(self, vals):
        if (
            "email" in vals
            and self.sudo().partner
            and not self.env.user.has_group("sales_team.group_sale_manager")
        ):
            raise models.ValidationError(
                _("Employee is now active: its email cannot be modified anymore!")
            )

        if "image_medium" in vals:
            if isinstance(vals["image_medium"], str):
                vals["image_medium"] = bytes(vals["image_medium"], "ascii")
            vals["image_medium"] = tools.image_resize_image_medium(vals["image_medium"])

        result = super().write(vals)

        if not self.active:
            self.action_revoke_portal_access()

        return result

    @api.multi
    def unlink(self):
        """Remove attachment before unlinking to avoid an Odoo v12 bug...

        ... namely the attachment is removed after the employee which
        then requires to be in group_user which is not the case for
        customers.

        see unlink in odoo/models.py (line 3211)
        """
        self.update({"image_medium": False})
        return super().unlink()

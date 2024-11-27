from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, Warning


class AutomatedControl(models.Model):
    _name = "commown_automated_control.automated_control"
    _description = "Interface class to define restricted base automation"

    _sql_constraints = [
        (
            "automation_uniq",
            "unique (base_automation_id)",
            "Automation already linked to an automated control",
        ),
    ]

    base_automation_id = fields.Many2one(
        "base.automation",
        "Linked base automation",
        ondelete="cascade",
        copy=False,
    )

    name = fields.Char(required=True)

    model_id = fields.Many2one(
        "ir.model",
        required=True,
        ondelete="cascade",
        domain=[("model", "in", ["project.task", "crm.lead"])],
        help="Model where the control is applied",
    )

    model_name = fields.Char(
        string="Model Name", compute="_compute_model_name", readonly=True, store=True
    )

    filter_pre_domain = fields.Char(
        related="base_automation_id.filter_pre_domain",
        readonly=False,
        copy=True,
    )

    filter_domain = fields.Char(
        related="base_automation_id.filter_domain",
        readonly=False,
        copy=True,
    )

    behaviour = fields.Selection(
        [
            ("raise", "Block the action with a message"),
            ("notify", "Notify the user with a messsage"),
        ],
        default="raise",
        required=True,
    )

    user_message = fields.Text("Message to display", required=True)

    internal_note = fields.Text(
        "Internal note, for documentation only",
        copy=False,
    )

    @api.onchange("model_id")
    def onchange_model_id(self):
        self.model_name = self.model_id.model

    @api.depends("model_id")
    def _compute_model_name(self):
        for rec in self:
            rec.model_name = rec.sudo().model_id.model

    @api.constrains("filter_domain")
    def _constrains_filter_domain(self):
        model = self.model_id.model
        domain = self.base_automation_id.filter_domain
        self._check_domain_restrictivity(model, domain)

    def _check_domain_restrictivity(self, model_name, domain):
        # Replace "required" attribute that doesn't work well on related fields
        if not domain:
            raise ValidationError(_("Application domain is mandatory, please set one"))

        # Check restrictivity
        required_field = {"project.task": "project_id", "crm.lead": "team_id"}[
            model_name
        ]
        field_name = self.env[model_name].fields_get()[required_field]["string"]

        if required_field not in domain:
            raise ValidationError(
                _("Domain is not restrictive enough. Please add a %s") % field_name
            )

    @api.model
    def execute(self):
        if self.behaviour == "raise":
            error_message = _(
                '%s\n\nThis message comes from automated control "%s" (id: %s)'
                % (self.user_message, self.name, self.id)
            )
            raise Warning(error_message)

        elif self.behaviour == "notify":
            title = "Message from automated control %r (id: %d)" % (self.name, self.id)
            self.env.user.notify_info(
                message=self.user_message,
                title=title,
                sticky=True,
            )

    @api.model
    def _compute_automation_name(self, name):
        return "[Commown][Automated Control] %s" % name

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        domain_dict = {
            d_name: vals[d_name]
            for d_name in ["filter_pre_domain", "filter_domain"]
            if d_name in vals
        }

        self._check_domain_restrictivity(
            self.env["ir.model"].browse(vals["model_id"]).model, vals["filter_domain"]
        )
        base_automation = (
            self.env["base.automation"]
            .sudo()
            .create(
                dict(
                    name=self._compute_automation_name(vals["name"]),
                    state="code",
                    trigger="on_write",
                    model_id=vals["model_id"],
                    **domain_dict,
                ),
            )
        )
        vals.pop("filter_domain")
        vals.pop("filter_pre_domain", None)

        new_rec = super().create(vals)

        new_rec.sudo().base_automation_id = base_automation.id
        new_rec.sudo().base_automation_id.code = (
            "env['commown_automated_control.automated_control'].browse(%d).execute()"
            % new_rec.id
        )

        return new_rec

    def write(self, vals):
        if "model_id" in vals:
            self.sudo().base_automation_id.model_id = vals["model_id"]

        if "name" in vals:
            self.sudo().base_automation_id.name = self._compute_automation_name(
                vals["name"]
            )

        return super().write(vals)

    @api.multi
    def unlink(self):
        automations = self.sudo().mapped("base_automation_id")
        super().unlink()
        automations.unlink()

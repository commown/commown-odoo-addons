from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    lang = fields.Selection(
        selection=lambda self: self.env['res.lang'].get_installed(),
        string='Language',
    )

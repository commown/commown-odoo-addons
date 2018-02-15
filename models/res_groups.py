import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CompletedGroup(models.Model):
    """ Complete res.groups with helper methods """
    _inherit = 'res.groups'

    @api.multi
    def add_users(self, users):
        ''' This method is used to circumvent python action "safe" eval: we
        cannot use |= operator. Wrapping it in a method works. '''
        for group in self:
            group.users |= users

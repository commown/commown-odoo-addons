from odoo import api, models


class CommownAccountMassReconcileMethod(models.Model):
    _inherit = 'account.mass.reconcile.method'

    @api.model
    def _get_all_rec_method(self):
        methods = super(CommownAccountMassReconcileMethod,
                        self)._get_all_rec_method()
        methods.append(('mass.reconcile.simple.partner_commown',
                        'Simple. Amount and Partner. Max date gap optimized.'))
        return methods

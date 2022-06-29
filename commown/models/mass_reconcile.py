from odoo import api, models


class CommownAccountMassReconcileMethod(models.Model):
    _inherit = 'account.mass.reconcile.method'

    @staticmethod
    def _get_reconcilation_methods():
        return [
            ('mass.reconcile.simple.name', 'Simple. Amount and Name'),
            ('mass.reconcile.simple.partner', 'Simple. Amount and Partner'),
            ('mass.reconcile.simple.reference',
             'Simple. Amount and Reference'),
            ('mass.reconcile.advanced.ref',
             'Advanced. Partner and Ref.'),
            ('mass.reconcile.simple.partner_commown',
             'Simple. Amount and Partner. Max date gap optimized.'),
        ]

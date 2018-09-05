from odoo.http import route, request
from odoo.addons.website_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    @route()
    def account(self, **kw):
        """ Add affiliation count to main account page """
        response = super(WebsiteAccount, self).account(**kw)
        Affiliate = request.env['sale.affiliate'].sudo()
        affiliate_count = Affiliate.search_count([
            ('partner_id', '=', request.env.user.partner_id.id),
        ])
        response.qcontext.update({
            'affiliate_count': affiliate_count,
        })
        return response

    @route('/my/affiliations', type='http', auth="user", website=True)
    def affiliations(self):
        Affiliate = request.env['sale.affiliate'].sudo()
        affiliates = Affiliate.search([
            ('partner_id', '=', request.env.user.partner_id.id),
        ])
        values = self._prepare_portal_layout_values()
        values['affiliates'] = affiliates
        return request.render("website_sale_affiliate_portal"
                              ".portal_my_affiliations", values)

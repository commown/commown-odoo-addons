import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SelfHelp(http.Controller):

    def _description(self, **post):
        view = request.env.ref('commown_self_troubleshooting.'
                               + post['issue-description-template'])
        return view.render(post)

    def _tag_ids(self, **post):
        env = request.env
        names = post.pop('tags', '').split(u',')
        ids = [
            env.ref('commown_self_troubleshooting.tag-self-troubleshooting').id,
            env.ref('commown_self_troubleshooting.tag-to-be-shipped').id,
        ]
        if names:
            ids.extend(env['project.tags'].search([('name', 'in', names)]).ids)
        if post.get('screwdriver', None) == 'yes':
            ids.append(
                env.ref('commown_self_troubleshooting.tag-need-screwdriver').id)
        return ids

    @http.route(['/self-troubleshoot'], type='http',
                auth='user', website=True)
    def create_support_card(self, **kw):
        _logger.info('create_support_card called with parameters %s', kw)
        env = request.env
        ref = env.ref
        post = request.params.copy()
        name = post.pop('self-troubleshoot-type')
        contract_id = int(post.pop('device_contract'))
        partner = env.user.partner_id
        issue = env['project.issue'].sudo().create({
            'name': name,
            'partner_id': partner.id,
            'description': self._description(**post),
            'project_id': ref(
                'commown_self_troubleshooting.support_project').id,
            'contract_id': contract_id,
            'tag_ids': [(6, 0, self._tag_ids(**post))]
        })
        env['mail.followers'].create({
            'res_model': issue._name,
            'res_id': issue.id,
            'partner_id': partner.id,
            'subtype_ids': [(6, 0, [
                ref('mail.mt_comment').id,
                ref('rating_project_issue.mt_issue_rating').id,
            ])],
        })
        return request.redirect('/my/issues/%d' % issue.id)

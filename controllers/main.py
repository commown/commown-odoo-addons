import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SelfHelp(http.Controller):

    action_tags = {'inform': ['tag-inform-only'],
                   'ship': ['tag-to-be-shipped']}

    def ref(self, suffix):
        return request.env.ref('commown_self_troubleshooting.' + suffix)

    def _description(self, **post):
        return self.ref(post['issue-description-template']).render(post)

    def _tag_ids(self, **post):
        ids = [self.ref(t).id for t in self.action_tags.get(post['action'], ())]
        ids.append(self.ref('tag-self-troubleshooting').id)
        names = post.get('tags', '').split(u',')
        if names:
            ids.extend(request.env['project.tags'].search(
                [('name', 'in', names)]).ids)
        if post.get('screwdriver', None) == 'yes':
            ids.append(self.ref('tag-need-screwdriver').id)
        return ids

    @http.route(['/self-troubleshoot'], type='http',
                auth='user', website=True)
    def create_support_card(self, **kw):
        _logger.info('create_support_card called with parameters %s', kw)
        env = request.env
        post = request.params.copy()
        name = post['self-troubleshoot-type']
        contract_id = int(post['device_contract'])
        partner = env.user.partner_id
        issue = env['project.issue'].sudo().create({
            'name': name,
            'partner_id': partner.id,
            'description': self._description(**post),
            'project_id': self.ref('support_project').id,
            'contract_id': contract_id,
            'tag_ids': [(6, 0, self._tag_ids(**post))]
        })
        env['mail.followers'].create({
            'res_model': issue._name,
            'res_id': issue.id,
            'partner_id': partner.id,
            'subtype_ids': [(6, 0, [
                env.ref('mail.mt_comment').id,
                env.ref('rating_project_issue.mt_issue_rating').id,
            ])],
        })
        return request.redirect('/my/issues/%d' % issue.id)

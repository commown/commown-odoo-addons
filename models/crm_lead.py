import cgi
import logging
from urllib import urlencode

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


EMAIL_RATINGS = [
    ('-1', 'No data'),
    ('0', 'No mail received'),
    ('1', 'Cold'),
    ('2', 'Neutral'),
    ('3', 'Warm'),
    ('4', 'Motivated'),
]

WEBID_RATINGS = [
    ('-1', 'No data'),
    ('0', 'Known strange'),
    ('1', 'Known neutral'),
    ('2', 'Known Coherent'),
]

TECHNICAL_SKILLS = [
    ('-1', 'No data'),
    ('0', 'neophyte'),
    ('1', 'intermediary'),
    ('2', 'confirmed'),
]

GLOBAL_FEELING = [
    ('-1', 'No data'),
    ('0', 'No go'),
    ('1', 'Suspicious'),
    ('2', 'Medium'),
    ('3', 'Pretty good'),
    ('4', 'No hesitation'),
]


class CommownCrmLead(models.Model):
    _inherit = 'crm.lead'

    email_rating = fields.Selection(
        EMAIL_RATINGS, string='Email Rating',
        default=EMAIL_RATINGS[0][0])
    web_searchurl = fields.Html(
        'Search on the web', compute='_compute_web_searchurl')
    webid_unknown = fields.Boolean(
        'Unknown on the web', default=False)
    webid_rating = fields.Selection(
        WEBID_RATINGS, string='Web identity Rating',
        default=WEBID_RATINGS[0][0])
    webid_notes = fields.Text('Notes')

    sent_collective_email = fields.Boolean(
        'Sent collective email', default=False)
    first_phone_call = fields.Boolean(
        '1st phone call', help='without leaving a message', default=False)
    second_phone_call = fields.Boolean(
        '2nd phone call', help='with a message', default=False)
    email_boost = fields.Boolean(
        'Email boost sent', default=False)
    third_phone_call = fields.Boolean(
        '3rd phone call', default=False)
    email_ultimatum = fields.Boolean(
        'Email ultimatum', default=False)
    registered_mail_sent = fields.Boolean(
        'Registered mail sent', default=False)

    orders_description = fields.Html(
        'Orders', sanitize_attributes=False)
    initial_data_notes = fields.Text('Notes')
    identity_validated = fields.Boolean(
        'Identity validated', default=False)
    mobile_validated = fields.Boolean(
        'Mobile phone validated', default=False)
    email_validated = fields.Boolean(
        'Email validated', default=False)
    billing_address_validated = fields.Boolean(
        'Billing address validated', default=False)
    delivery_address_validated = fields.Boolean(
        'Delivery address validated', default=False)
    address_hesitation = fields.Boolean(
        'Address spelling hesitation', default=False)
    technical_skills = fields.Selection(
        TECHNICAL_SKILLS, string='Technical skills',
        default=TECHNICAL_SKILLS[0][0])
    questions = fields.Text('Customer questions')
    global_feeling = fields.Selection(
        GLOBAL_FEELING, string='Global feeling',
        default=GLOBAL_FEELING[0][0])
    comments = fields.Text('Comments')

    expedition_ref = fields.Text("Expedition reference", size=64)
    expedition_date = fields.Date("Expedition Date")
    delivery_date = fields.Date("Delivery Date")

    def _onchange_partner_id_values(self, partner_id):
        vals = super(CommownCrmLead, self)._onchange_partner_id_values(
            partner_id)
        vals['orders_description'] = self._compute_orders_descr(partner_id)
        return vals

    def _compute_orders_descr(self, partner_id=None):
        # XXX Use a qweb template
        if partner_id is None:
            partner_id = self.partner_id
        if not partner_id:
            return ''
        orders = self.env['sale.order'].search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'sent'),
        ])
        descr = []
        for order in orders:
            descr.append(u'<h4>%s</h4>' % cgi.escape(order.name, quote=True))
            oline_descr = []
            for oline in order.order_line:
                oline_descr.append(u'<li>%s</li>' % cgi.escape(
                    oline.product_id.display_name, quote=True))
            descr.append(u'<ul>%s</ul>' % u'\n'.join(oline_descr))
        return u'\n'.join(descr)

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        partner_id = vals.get('partner_id', False)
        if 'orders_description' not in vals:
            vals['orders_description'] = self._compute_orders_descr(partner_id)
        # CRM module does not seem to update partner values for now
        vals.update(self._onchange_partner_id_values(partner_id))
        return super(CommownCrmLead, self).create(vals)

    @api.model
    def action_customisable_form_view(self):
        ctx = self.env.context
        action = self.env.ref(
            'crm.crm_case_form_view_salesteams_opportunity').read()[0]
        action['context'] = safe_eval(action['context'], self.env.context)
        # XXX improve me with a custom_lead_form_view field on crm_team
        custom_team_id = 'sales_team.salesteam_website_sales'
        if ctx.get('active_model') == 'crm.team' and 'active_id' in ctx:
            crm_team = self.env['crm.team'].browse(ctx['active_id'])
            if crm_team.get_xml_id()[ctx['active_id']] == custom_team_id:
                custom_view = self.env.ref('commown.crm_case_form_view_oppor')
                action['views'] = [
                    [id if type != 'form' else custom_view.id, type]
                    for id, type in action['views']]
        return action

    @api.multi
    def _compute_web_searchurl(self):
        for lead in self:
            # XXX template me!
            query = u' '.join((lead.contact_name or u'',
                               lead.city or u'')).strip().encode('utf-8')
            url = u'http://www.google.fr/search?%s' % urlencode({'q': query})
            lead.web_searchurl = (
                u"<a target='_blank' href='%s'>%s</a>"
                % (cgi.escape(url, quote=True),
                   cgi.escape(_('Web search link'), quote=True)))

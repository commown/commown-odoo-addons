import cgi
import json
import logging
import os
import re
from base64 import b64encode
from datetime import datetime
from subprocess import check_call, CalledProcessError
from tempfile import gettempdir, mktemp
from urllib import urlencode

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval

from colissimo_utils import ship

LEAD_NAME_RE = re.compile(r'\[(?P<order_num>SO[0-9]+)\].*')

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
    expedition_status = fields.Text("Expedition status", size=256)
    expedition_status_fetch_date = fields.Datetime(
        "Expedition status fetch date")
    expedition_urgency_mail_sent = fields.Boolean(
        "Expedition urgency mail send", default=False)
    delivery_date = fields.Date("Delivery Date")

    def _onchange_partner_id_values(self, partner_id):
        vals = super(CommownCrmLead, self)._onchange_partner_id_values(
            partner_id)
        vals['orders_description'] = self._compute_orders_descr(partner_id)
        return vals

    def _compute_orders_descr(self, partner_id=None):
        # XXX Use a qweb template
        if partner_id is None:
            partner_id = self.partner_id.id
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
        """ Customize the view to be used for leads of a sales team dashboard

        This method is called from a server-action so we can dynamically decide
        which view is to be used (=the custom sales team's lead view, if any).
        """
        ctx = self.env.context
        action = self.env.ref(
            'crm.crm_case_form_view_salesteams_opportunity').read()[0]
        action['context'] = safe_eval(action['context'], self.env.context)
        if ctx.get('active_model') == 'crm.team' and 'active_id' in ctx:
            crm_team = self.env['crm.team'].browse(ctx['active_id'])
            custom_view = crm_team.custom_lead_view_id
            if custom_view:
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

    @api.multi
    def _create_colissimo_fairphone_label(self):
        self.ensure_one()
        login = self.env.context['colissimo_login']
        password = self.env.context['colissimo_password']
        sender_email = self.env.context['colissimo_sender_email']
        commercial_name = self.env.context['colissimo_commercial_name']
        sender = self.env['res.partner'].search([('email', '=', sender_email)])
        match = LEAD_NAME_RE.match(self.name)
        order_number = match.groupdict()['order_num'] if match else ''
        recipient = self.partner_id
        meta_data, label_data = ship(
            login, password, sender, recipient, order_number,
            commercial_name)
        if meta_data and not label_data:
            raise ValueError(json.dumps(meta_data))
        assert meta_data and label_data
        self.expedition_ref = meta_data['labelResponse']['parcelNumber']
        self.expedition_date = datetime.today()
        return self.env['ir.attachment'].create({
            'res_model': 'crm.lead',
            'res_id': self.id,
            'mimetype': u'application/pdf',
            'datas': b64encode(label_data),
            'datas_fname': self.expedition_ref + '.pdf',
            'name': 'colissimo.pdf',
            'public': False,
            'type': 'binary',
        })

    def write(self, vals, **kwargs):
        "Remove the colissimo label attachment when expedition_ref is emptied."
        if 'expedition_ref' in vals and not vals['expedition_ref']:
            domain = [
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', self.id),
                ('name', '=', 'colissimo.pdf'),
            ]
            for att in self.env['ir.attachment'].search(domain):
                _logger.error('REMOVE att %s of lead %s', att.id, self.id)
                att.unlink()
        return super(CommownCrmLead, self).write(vals, **kwargs)

    @api.multi
    def colissimo_fairphone_label(self):
        " Return current label if expedition_ref is set, or create a new one "
        self.ensure_one()
        domain = [
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.id),
            ('name', '=', 'colissimo.pdf'),
            ]
        current = self.env['ir.attachment'].search(domain)
        if not current:
            current = self._create_colissimo_fairphone_label()
        return current[0]

    @api.multi
    def colissimo_fairphone_labels(self):
        paths = []

        for lead in self:
            label = lead.colissimo_fairphone_label()
            paths.append(label._full_path(label.store_fname))

        fpath = os.path.join(gettempdir(), mktemp(suffix=".pdf"))
        result_path = None
        try:
            check_call(['pdftk'] + paths + ['cat', 'output', fpath])
            check_call([
                'pdfjam', '--nup', '2x2', '--offset', '0.1cm 2.4cm',
                '--trim', '1.95cm 5.8cm 17.4cm 2.5cm', '--clip', 'true',
                '--frame', 'false', '--scale', '0.98',
                '--outfile', gettempdir(), fpath])
            result_path = fpath[:-4] + '-pdfjam' + fpath[-4:]

        except CalledProcessError:
            fpath = None
            raise ValueError('PDF concatenation or assembly failed')

        else:
            with open(result_path) as fobj:
                data = b64encode(fobj.read())
            sales = self[0].team_id
            attrs = {'res_model': 'crm.team',
                     'res_id': sales.id,
                     'name': 'colissimo.pdf',
                     }
            domain = [(k, '=', v) for k, v in attrs.items()]
            for att in self.env['ir.attachment'].search(domain):
                att.unlink()
            attrs.update({
                'mimetype': u'application/pdf',
                'datas': data,
                'datas_fname': 'colissimo.pdf',
                'public': False,
                'type': 'binary',
                })
            return self.env['ir.attachment'].create(attrs)

        finally:
            for p in (fpath, result_path):
                if p is None:
                    continue
                try:
                    os.unlink(p)
                except:
                    _logger.error('Could not remove tmp label file %r', p)

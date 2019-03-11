import json
import logging
import os
import re
from base64 import b64encode
from datetime import datetime
from subprocess import check_call, CalledProcessError
from tempfile import gettempdir, mktemp

from odoo import models, fields, api

from colissimo_utils import ship

LEAD_NAME_RE = re.compile(r'\[(?P<order_num>SO[0-9]+).*')

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    expedition_ref = fields.Text("Expedition reference", size=64)
    expedition_date = fields.Date("Expedition Date")
    expedition_status = fields.Text("Expedition status", size=256)
    expedition_status_fetch_date = fields.Datetime(
        "Expedition status fetch date")
    expedition_urgency_mail_sent = fields.Boolean(
        "Expedition urgency mail send", default=False)
    delivery_date = fields.Date("Delivery Date")
    start_contract_on_delivery = fields.Boolean(
        default=True, string='Automatic contract start on delivery')
    send_email_on_delivery = fields.Boolean(
        default=True, string='Automatic email on delivery')
    on_delivery_email_template_id = fields.Many2one(
        'mail.template', string='Custom email model for this lead')

    @api.multi
    def _create_colissimo_fairphone_label(self):
        self.ensure_one()
        login = self.env.context['colissimo_login']
        password = self.env.context['colissimo_password']
        sender_email = self.env.context['colissimo_sender_email']
        commercial_name = self.env.context['colissimo_commercial_name']
        is_return = self.env.context.get('colissimo_is_return', False)
        sender = self.env['res.partner'].search([('email', '=', sender_email)])
        match = LEAD_NAME_RE.match(self.name)
        order_number = match.groupdict()['order_num'] if match else ''
        recipient = self.partner_id
        if is_return:
            sender, recipient = recipient, sender
        meta_data, label_data = ship(
            login, password, sender, recipient, order_number,
            commercial_name, is_return)
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
                _logger.warning('REMOVE att %s of lead %s', att.id, self.id)
                att.unlink()
        return super(CrmLead, self).write(vals, **kwargs)

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
        if (len(self) == 1 and
                self.env.context.get('colissimo_force_single_label', False)):
            return self.colissimo_fairphone_label()

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

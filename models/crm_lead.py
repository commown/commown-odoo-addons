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

LEAD_NAME_RE = re.compile(r'\[(?P<order_num>[^\]]+)\].*')

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
        """ Generate a new colissimo label based on the information found in
        the context, which names are prefixed by "colissimo_":

        - "colissimo_account" must be set to the login of a keychain account
          which namespace is colissimo
        - "colissimo_sender_email" must be set to the sender partner's email
        - the other `colissimo_utils.shipping_data` argument names prefixed by
          "colissimo_" if required (see their default value in this function's
          docstring).
        """
        self.ensure_one()
        prefix = 'colissimo_'
        kwargs = {k[len(prefix):]: v for k, v in self.env.context.items()
                      if k.startswith(prefix)}

        if 'commercial_name' not in kwargs:
            kwargs['commercial_name'] = self.env.ref('base.main_company').name

        match = LEAD_NAME_RE.match(self.name)
        kwargs.setdefault('order_number',
                          match.groupdict()['order_num'] if match else '')

        kwargs['sender'] = self.env['res.partner'].search([
            ('email', '=', kwargs.pop('sender_email')),
        ])
        kwargs['recipient'] = self.partner_id
        if kwargs.get('is_return', False):
            kwargs['sender'], kwargs['recipient'] = (
                kwargs['recipient'], kwargs['sender']
)
        account = self.env['keychain.account'].sudo().retrieve([
            ('namespace', '=', 'colissimo'),
            ('login', '=', kwargs.pop('account')),
        ]).ensure_one()

        meta_data, label_data = ship(account.login, account._get_password(),
                                     **kwargs)

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
            # Remove colissimo_force_single_label from context as lower-level
            # shippping functions do not expect it
            context = dict(self.env.context)
            context.pop('colissimo_force_single_label')
            return self.with_context(context).colissimo_fairphone_label()

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

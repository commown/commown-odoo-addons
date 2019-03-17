import json
import logging
import os
import re
from base64 import b64encode
from datetime import datetime
from subprocess import check_call, CalledProcessError
from tempfile import gettempdir, mktemp

from odoo import models, fields, api


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
    def _create_parcel_label(self, parcel_name, account, sender, recipient,
                             ref):
        """ Generate a new label from following arguments:
        - parcel_name: the name of a ParcelType entity
        - account: the login of a keychain account which namespace is colissimo
        - sender: the sender partner
        - recipient: the recipient partner
        - ref: a reference to be printed on the parcel
        """
        self.ensure_one()

        parcel_type = self.env['commown.parcel.type'].search([
            ('name', '=', parcel_name),
        ])

        meta_data, label_data = parcel_type.colissimo_label(
            account, sender, recipient, ref)

        if meta_data and not label_data:
            raise ValueError(json.dumps(meta_data))
        assert meta_data and label_data

        self.expedition_ref = meta_data['labelResponse']['parcelNumber']
        self.expedition_date = datetime.today()
        return self.env['ir.attachment'].create({
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': u'application/pdf',
            'datas': b64encode(label_data),
            'datas_fname': self.expedition_ref + '.pdf',
            'name': parcel_name + '.pdf',
            'public': False,
            'type': 'binary',
        })

    @api.multi
    def label_attachment(self, parcel_name):
        self.ensure_one()
        domain = [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('name', '=', parcel_name + u'.pdf'),
            ]
        return self.env['ir.attachment'].search(domain)

    @api.multi
    def _get_or_create_label(self, parcel_name, *args, **kwargs):
        " Return current label if expedition_ref is set, or create a new one "
        self.ensure_one()
        return (self.label_attachment(parcel_name)
                or self._create_parcel_label(parcel_name, *args, **kwargs))

    @api.multi
    def get_label_ref(self):
        self.ensure_one()
        match = LEAD_NAME_RE.match(self.name)
        return match.groupdict()['order_num'] if match else ''

    @api.multi
    def parcel_labels(self, parcel_name, account, sender, recipient,
                      force_single=False, ref=None):

        if len(self) == 1 and force_single:
            ref = ref if ref is not None else self.get_label_ref()
            return self._get_or_create_label(
                parcel_name, account, sender, recipient, ref)

        paths = []

        for lead in self:
            ref = ref if ref is not None else lead.get_label_ref()
            label = lead._get_or_create_label(
                parcel_name, account, sender, recipient, ref)
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
                     'name': parcel_name + u'.pdf',
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

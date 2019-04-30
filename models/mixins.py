import logging
import json
import os
import re
from base64 import b64encode
from datetime import datetime
from subprocess import check_call, CalledProcessError
from tempfile import gettempdir, mktemp

from odoo import api, models, fields


REF_FROM_NAME_RE = re.compile(r'\[(?P<ref>[^\]]+)\].*')

_logger = logging.getLogger(__name__)


class CommownShippingMixin(models.AbstractModel):
    _name = 'commown.shipping.mixin'

    # Needs to be overloaded: used to store multiple label pdfs
    # (when printing several labels at once)
    _shipping_parent_rel = None

    @api.multi
    def _create_parcel_label(self, parcel, account, sender, recipient, ref):
        """ Generate a new label from following arguments:
        - parcel: a commown.parcel.type entity
        - account: a keychain.account entity which namespace is "colissimo"
        - sender: the sender res.partner entity
        - recipient: the recipient res.partner entity
        - ref: a string reference to be printed on the parcel
        """
        self.ensure_one()

        meta_data, label_data = parcel.colissimo_label(
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
            'name': parcel.name + '.pdf',
            'public': False,
            'type': 'binary',
        })

    @api.multi
    def label_attachment(self, parcel):
        self.ensure_one()
        domain = [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('name', '=', parcel.name + u'.pdf'),
            ]
        return self.env['ir.attachment'].search(domain)

    @api.multi
    def _get_or_create_label(self, parcel, *args, **kwargs):
        " Return current label if expedition_ref is set, or create a new one "
        self.ensure_one()
        return (self.label_attachment(parcel)
                or self._create_parcel_label(parcel, *args, **kwargs))

    @api.multi
    def get_label_ref(self):
        self.ensure_one()
        match = REF_FROM_NAME_RE.match(self.name)
        return match.groupdict()['ref'] if match else ''

    @api.multi
    def parcel_labels(self, parcel_name, account_name, sender,
                      force_single=False, ref=None):

        parcel = self.env['commown.parcel.type'].search([
            ('technical_name', '=', parcel_name),
        ]).ensure_one()

        account = self.env['keychain.account'].search([
            ('technical_name', '=', account_name),
        ]).ensure_one()

        if len(self) == 1 and force_single:
            ref = ref if ref is not None else self.get_label_ref()
            return self._get_or_create_label(
                parcel, account, sender, self.partner_id, ref)

        paths = []

        for lead in self:
            ref = ref if ref is not None else lead.get_label_ref()
            label = lead._get_or_create_label(
                parcel, account, sender, lead.partner_id, ref)
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
            parent = getattr(self[0], self._shipping_parent_rel)
            attrs = {'res_model': parent._name,
                     'res_id': parent.id,
                     'name': parcel.name + u'.pdf',
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


class CommownShippingParentMixin(models.AbstractModel):
    _name = 'commown.shipping.parent.mixin'

    shipping_account_id = fields.Many2one(
        'keychain.account', string='Shipping account',
        domain="[('namespace', '=', 'colissimo')]")

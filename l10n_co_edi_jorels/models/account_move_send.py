# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of l10n_co_edi_jorels.
#
# l10n_co_edi_jorels is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_mail_attachments_widget(self, move, mail_template, extra_edis=None, pdf_report=None):
        res = super()._get_default_mail_attachments_widget(move, mail_template)
        return res + self._get_invoice_edi_attachments_data(move)

    def _get_invoice_edi_attachments_data(self, move):
        if not move.company_id.ei_enable or not move.is_to_send_edi_email():
            return []

        attached_document_name = move._compute_attached_document_name()
        zip_name = f"{attached_document_name}.zip"

        attachment = self.env['ir.attachment'].create({
            'name': zip_name,
            'datas': move.ei_attached_zip_base64_bytes,
            'res_model': 'account.move',
            'res_id': move.id,
            'type': 'binary',
            'mimetype': 'application/zip',
        })

        return [{
            'id': attachment.id,
            'name': zip_name,
            'mimetype': attachment.mimetype,
            'placeholder': False,
            'protect_from_deletion': True,
        }]

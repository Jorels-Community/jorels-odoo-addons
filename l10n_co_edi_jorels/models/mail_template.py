# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2019-2022)
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

import base64
import zipfile
from io import BytesIO

from odoo import models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def generate_email(self, res_ids, fields):
        res = super(MailTemplate, self).generate_email(res_ids, fields)

        self.ensure_one()

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        records = self.env[self.model].browse(res_ids)

        if self.model == 'account.move':
            for move in records:
                inv_default_template = self.env.ref('account.email_template_edi_invoice')
                ei_template = self.env.ref('l10n_co_edi_jorels.email_template_edi')
                if self.id in (ei_template.id, inv_default_template.id):

                    if not move.company_id.ei_enable:
                        continue

                    res_t = multi_mode and res[move.id] or res

                    if 'attachments' not in res_t:
                        res_t['attachments'] = []
                    attachments = res_t['attachments'] if move.company_id.ei_include_pdf_attachment else []

                    if move.is_to_send_edi_email():
                        if move.ei_zip_name:
                            attached_document_name = 'ad' + move.ei_zip_name[1:-4]
                        else:
                            attached_document_name = move.ei_uuid

                        # Create main zip buffer
                        main_zip_buffer = BytesIO()
                        zip_name = attached_document_name + '.zip'
                        with zipfile.ZipFile(main_zip_buffer, 'w') as main_zip:
                            # Add PDF to main zip
                            pdf_name = attached_document_name + '.pdf'
                            pdf_content = base64.decodebytes(res_t['attachments'][0][1])
                            main_zip.writestr(pdf_name, pdf_content)

                            # Add XML to main zip
                            xml_name = attached_document_name + '.xml'
                            xml_content = base64.decodebytes(move.ei_attached_document_base64_bytes)
                            main_zip.writestr(xml_name, xml_content)

                            # If there are additional documents, create a secondary zip
                            if move.ei_additional_documents:
                                additional_zip_buffer = BytesIO()
                                with zipfile.ZipFile(additional_zip_buffer, 'w') as additional_zip:
                                    for attachment in move.ei_additional_documents:
                                        additional_zip.writestr(attachment.name, base64.b64decode(attachment.datas))
                                
                                # Add secondary zip to main zip
                                main_zip.writestr(attached_document_name + '_additional_documents.zip', additional_zip_buffer.getvalue())

                        # Encode main zip content
                        main_zip_content = main_zip_buffer.getvalue()
                        ei_attached_zip_base64_bytes = base64.b64encode(main_zip_content)
                        
                        # Add main zip to email attachments
                        attachments += [(zip_name, ei_attached_zip_base64_bytes)]
                        
                        # Update move with new zip content
                        move.write({
                                'ei_attached_zip_base64_bytes': ei_attached_zip_base64_bytes
                            })

                        res_t["attachments"] = attachments

        elif self.model == 'l10n_co_edi_jorels.radian':
            for radian in records:

                if not radian.company_id.ei_enable:
                    continue

                res_t = multi_mode and res[radian.id] or res

                if 'attachments' not in res_t:
                    res_t['attachments'] = []
                attachments = res_t['attachments'] if radian.company_id.ei_include_pdf_attachment else []
                # attachments = []

                if radian.edi_is_valid \
                        and radian.state == 'posted'\
                        and radian.edi_uuid\
                        and radian.edi_attached_document_base64:

                    if radian.edi_zip_name:
                        attached_document_name = 'ad' + radian.edi_zip_name[1:-4]
                    else:
                        attached_document_name = radian.edi_uuid

                    # Create main zip buffer
                    main_zip_buffer = BytesIO()
                    zip_name = attached_document_name + '.zip'

                    with zipfile.ZipFile(main_zip_buffer, 'w') as zip_archive:
                        # Add XML to zip
                        xml_name = attached_document_name + '.xml'
                        xml_content = base64.decodebytes(radian.edi_attached_document_base64)
                        zip_archive.writestr(xml_name, xml_content)

                    # Encode zip content
                    zip_content = main_zip_buffer.getvalue()
                    edi_attached_zip_base64 = base64.b64encode(zip_content)

                    # Add zip to email attachments
                    attachments += [(zip_name, edi_attached_zip_base64)]

                    # Update radian with new zip content
                    radian.write({
                        'edi_attached_zip_base64': edi_attached_zip_base64
                    })

                    res_t["attachments"] = attachments

        return res

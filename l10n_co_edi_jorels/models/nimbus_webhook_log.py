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

from odoo import api, fields, models, _


class NimbusWebhookLog(models.Model):
    _name = 'l10n_co_edi_jorels.nimbus_webhook_log'
    _description = 'Log de webhooks recibidos de NIMBUS'
    _order = 'create_date desc'

    company_id = fields.Many2one('res.company', string="Compañía", required=True,
                                 default=lambda self: self.env.user.company_id)
    delivery_id = fields.Char(string="Delivery ID", required=True, index=True)
    event_type = fields.Char(string="Tipo de evento")
    edi_id = fields.Integer(string="EDI ID")
    timestamp = fields.Datetime(string="Timestamp del evento")
    payload = fields.Text(string="Payload completo")
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('done', 'Procesado'),
        ('error', 'Error'),
    ], default='pending')
    invoice_id = fields.Many2one('account.invoice', string="Factura creada")
    event_id = fields.Many2one('l10n_co_edi_jorels.radian', string="Evento creado")
    error_message = fields.Text(string="Mensaje de error")

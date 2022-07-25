# -*- coding: utf-8 -*-
#
#   l10n_co_edi_jorels
#   Copyright (C) 2022  Jorels SAS
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published
#   by the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#   email: info@jorels.com
#

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class Webhooks(http.Controller):

    @http.route('/l10n_co_edi_jorels/webhook/in_invoice/<company_id>', type='json', auth='public', methods=['POST'],
                csrf=False)
    def webhook_in_invoice(self, company_id, **args):
        # journal_id = 2
        # partner_id = 1
        # json_example = {'a': 1, 'b': 2, 'c': '3', 'd': '4'}

        # data = json.loads(request.httprequest.args)
        data = json.loads(request.httprequest.data)

        # request.env['account.move'].sudo().create({
        #     'partner_id': partner_id,
        #     'journal_id': journal_id,
        #     'move_type': 'in_invoice',
        #     'comment': data
        # })

        _logger.debug("webhook_in_invoice: company_id: %s, json: %s", company_id, data)
        return "Test Ok"

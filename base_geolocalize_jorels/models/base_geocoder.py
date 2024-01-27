# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of base_geolocalize_jorels.
#
# base_geolocalize_jorels is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# base_geolocalize_jorels is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with base_geolocalize_jorels.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import logging

import requests
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GeoCoder(models.AbstractModel):
    _inherit = "base.geocoder"

    @api.model
    def _call_jorelsmap(self, addr, **kw):
        """ Use Jorels Maps API. It won't work without a valid API key.
        :return: (latitude, longitude, zip, street) or None if not found
        """
        token = self.env['ir.config_parameter'].sudo().get_param('jorels.ody_api_key')
        if not token:
            raise UserError(_(
                "Jorels Maps Api key for GeoCoding required.\n"
                "Visit https://www.jorels.com for more information."
            ))

        url = "https://ody.jorels.com/geocode"

        header = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        }

        params = {'q': addr}

        try:
            result = requests.get(url, headers=header, params=params).json()
        except Exception as e:
            self._raise_query_error(e)

        try:
            lat = result['geo']['lat']
            lng = result['geo']['lng']
            zip = result['zip']
            street = result['street']

            return float(lat), float(lng), zip, street
        except (KeyError, ValueError, IndexError):
            return None

    @api.model
    def _geo_query_address_jorels(self, street=None, zip=None, city=None, state=None, country=None):
        return self._geo_query_address_default(street=street, zip=zip, city=city, state=state, country=country)

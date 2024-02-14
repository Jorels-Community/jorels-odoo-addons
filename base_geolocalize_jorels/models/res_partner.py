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

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    geolocated_address = fields.Char(string='Geolocated address')

    def geo_localize_jorels(self):
        for partner in self.with_context(lang='en_US'):
            result = self._geo_localize(partner.street,
                                        partner.zip,
                                        partner.city,
                                        partner.state_id.name,
                                        partner.country_id.name)
            if result:
                partner.write({
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'zip': result[2],
                    'geolocated_address': result[3],
                    'date_localization': fields.Date.context_today(partner)
                })
        return True

    def geo_localize(self):
        provider = self.env['base.geocoder']._get_provider().tech_name
        if provider == 'jorelsmap':
            res = self.geo_localize_jorels()
        else:
            res = super(ResPartner, self).geo_localize()
        return res

    def button_geo_link(self):
        for rec in self:
            geo_lat = str(rec.partner_latitude)
            geo_lng = str(rec.partner_longitude)
            geo = "https://www.google.com/maps?q={},{}".format(geo_lat, geo_lng)
            return {
                "type": "ir.actions.act_url",
                "url": geo,
                "target": "new",
            }

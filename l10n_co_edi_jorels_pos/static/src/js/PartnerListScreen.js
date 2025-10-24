/*
*   Jorels S.A.S. - Copyright (C) 2019-2023
*
*   This file is part of l10n_co_edi_jorels_pos.
*
*   This program is free software: you can redistribute it and/or modify
*   it under the terms of the GNU Lesser General Public License as published by
*   the Free Software Foundation, either version 3 of the License, or
*   (at your option) any later version.
*
*   This program is distributed in the hope that it will be useful,
*   but WITHOUT ANY WARRANTY; without even the implied warranty of
*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*   GNU Lesser General Public License for more details.
*
*   You should have received a copy of the GNU Lesser General Public License
*   along with this program. If not, see <https://www.gnu.org/licenses/>.
*
*   email: info@jorels.com
*/

odoo.define('l10n_co_edi_jorels_pos.PartnerListScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const PartnerListScreen = require('point_of_sale.PartnerListScreen');

    const JPartnerListScreen = (PartnerListScreen) =>
        class extends PartnerListScreen {
            _getDefaultPartner() {
                if (this.env.pos.company.ei_enable && this.env.pos.company.ei_set_default_partner_data) {
                    return {
                        name: 'Consumidor Final',
                        country_id: this.env.pos.company.country_id,
                        state_id: this.env.pos.company.state_id,
                        vat: '222222222222',
                        company_type: 'person',
                        city: this.env.pos.company.city,
                        l10n_latam_identification_type_id: [this.env.pos.l10n_latam_identification_types.find(o => o.l10n_co_document_code=='national_citizen_id')['id']],
                        type_regime_id: [2],
                        type_liability_id: [29],
                        municipality_id: this.env.pos.company.municipality_id
                    };
                }

                return {};
            }

            createPartner() {
                super.createPartner(...arguments);
                this.state.editModeProps.partner = Object.assign({}, this.state.editModeProps.partner,
                    this._getDefaultPartner()
                );
            }

            deactivateEditMode() {
                super.deactivateEditMode();
                // Reset to default values when closing the editor
                const defaultPartner = this._getDefaultPartner();
                if (Object.keys(defaultPartner).length > 0) {
                    this.state.editModeProps.partner = Object.assign({}, this.state.editModeProps.partner, defaultPartner);
                }
            }
        };
    Registries.Component.extend(PartnerListScreen, JPartnerListScreen);

    return PartnerListScreen;
});
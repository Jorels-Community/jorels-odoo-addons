/** @odoo-module */

// Jorels S.A.S. - Copyright (2019-2024)
//
// This file is part of l10n_co_edi_jorels_pos.
//
// l10n_co_edi_jorels_pos is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// l10n_co_edi_jorels_pos is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with l10n_co_edi_jorels_pos.  If not, see <https://www.gnu.org/licenses/>.
//
// email: info@jorels.com
//

import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerListScreen.prototype, {
    _getDefaultPartner() {
        if (this.pos.is_colombian_country() && this.pos.company.ei_enable && this.pos.company.ei_set_default_partner_data) {
            return {
                name: 'Consumidor Final',
                country_id: this.pos.company.country_id,
                state_id: this.pos.company.state_id,
                vat: '222222222222',
                company_type: 'person',
                city: this.pos.company.city,
                l10n_latam_identification_type_id: [this.pos.l10n_latam_identification_types.find(o => o.l10n_co_document_code=='national_citizen_id')['id']],
                type_regime_id: [2],
                type_liability_id: [29],
                municipality_id: this.pos.company.municipality_id
            };
        }
        return {};
    },

    createPartner() {
        super.createPartner(...arguments);
        if (this.pos.is_colombian_country()) {
            this.state.editModeProps.partner = Object.assign({}, this.state.editModeProps.partner, this._getDefaultPartner());
        }
    },

    deactivateEditMode() {
        super.deactivateEditMode(...arguments);
        if (this.pos.is_colombian_country()) {
            this.state.editModeProps.partner = Object.assign({}, this.state.editModeProps.partner, this._getDefaultPartner());
        }
    },
});

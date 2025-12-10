/** @odoo-module */

// Jorels S.A.S. - Copyright (2019-2025)
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

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * Override editPartnerContext to provide default values for Colombian partners.
     * In Odoo 18, this method returns additional context for the partner form.
     * We use the 'default_' prefix to set default values for new partners.
     */
    editPartnerContext(partner) {
        const context = super.editPartnerContext(...arguments);

        // Only apply defaults for new partners (when partner is falsy)
        if (!partner && this.is_colombian_country() && this.company.ei_enable && this.company.ei_set_default_partner_data) {
            const identType = this.l10n_latam_identification_types?.find(
                o => o.l10n_co_document_code === 'national_citizen_id'
            );

            return {
                ...context,
                default_name: 'Consumidor Final',
                default_country_id: this.company.country_id?.[0],
                default_state_id: this.company.state_id?.[0],
                default_vat: '222222222222',
                default_company_type: 'person',
                default_city: this.company.city,
                default_l10n_latam_identification_type_id: identType?.id,
                default_type_regime_id: 2,
                default_type_liability_id: 29,
                default_municipality_id: this.company.municipality_id?.[0],
            };
        }

        return context;
    },
});

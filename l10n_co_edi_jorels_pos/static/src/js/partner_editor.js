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

import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerDetailsEdit.prototype, {
    setup(){
        super.setup(...arguments);
        if (this.pos.is_colombian_country()) {
            this.intFields.push(
                'l10n_latam_identification_type_id',
                'type_regime_id',
                'type_liability_id',
                'municipality_id'
            );
            const partner = this.props.partner;
            this.changes.company_type = partner.company_type
            this.changes.l10n_latam_identification_type_id = partner.l10n_latam_identification_type_id && partner.l10n_latam_identification_type_id[0]
            this.changes.type_regime_id = partner.type_regime_id && partner.type_regime_id[0]
            this.changes.type_liability_id = partner.type_liability_id && partner.type_liability_id[0]
            this.changes.municipality_id = partner.municipality_id && partner.municipality_id[0]
            this.changes.email = partner.email || ""
            this.changes.email_edi = partner.email_edi || ""
            this.changes.edi_dian_acquirer_email = partner.edi_dian_acquirer_email || ""
            this.changes.edi_dian_acquirer_name = partner.edi_dian_acquirer_name || ""
        }
    },

    formatColombianName(name) {
        /**
         * Formats a Colombian name assuming the first two words are last names
         * and the remaining words are first names.
         *
         * @param {string} name - Full name with last names first
         * @returns {string} Formatted name as "Last Names, First Names"
         */
        const words = name.trim().split(/\s+/);

        if (words.length < 2) {
            return name;
        }

        if (words.length === 2) {
            return `${words[0]}, ${words[1]}`;
        }

        const lastNames = words.slice(0, 2).join(' ');
        const firstNames = words.slice(2).join(' ');

        return `${lastNames}, ${firstNames}`;
    },

    async getDianAcquirer() {
        const vat = this.changes.vat || this.props.partner.vat;
        const l10nLatamTypeId = this.changes.l10n_latam_identification_type_id ||
                               (this.props.partner.l10n_latam_identification_type_id && this.props.partner.l10n_latam_identification_type_id[0]);

        try {
            const result = await this.env.services.orm.call(
                'res.partner',
                'fetch_dian_acquirer_data_latam_type',
                [l10nLatamTypeId, vat],
            );

            if (result) {
                this.updateFieldValue('edi_dian_acquirer_email', result.email || '');
                this.updateFieldValue('edi_dian_acquirer_name', result.name || '');
            }
            else{
                this.env.services.popup.add('ErrorPopup', {
                    title: 'Sin datos en consulta DIAN',
                    body: 'No se obtuvieron datos al consultar en la DIAN.',
                });
            }
        } catch (error) {
            // Extract the error message from Odoo's error structure
            let errorMessage = 'Error al consultar los datos en la DIAN.';

            // Check the nested structure for the actual error message
            if (error.message && error.message.data && error.message.data.message) {
                errorMessage = error.message.data.message;
            } else if (error.data && error.data.message) {
                errorMessage = error.data.message;
            } else if (error.message) {
                errorMessage = error.message;
            }

            this.env.services.popup.add('ErrorPopup', {
                title: 'Error en consulta DIAN',
                body: errorMessage,
            });
        }
    },

    updateFieldValue(fieldName, value) {
        // Update the changes object
        this.changes[fieldName] = value;

        // Trigger a render to update the UI
        this.render();
    },

    async acquirerReplace() {
        // Transfer DIAN data to form fields
        if (this.changes.edi_dian_acquirer_name && this.changes.edi_dian_acquirer_email) {
            const companyType = this.changes.company_type || this.props.partner.company_type;

            // Update name
            let formattedName;
            if (companyType === 'company') {
                formattedName = this.changes.edi_dian_acquirer_name;
            }
            else {
                formattedName = this.formatColombianName(this.changes.edi_dian_acquirer_name);
            }
            this.updateFieldValue('name', formattedName);

            // Update Edi email
            this.updateFieldValue('email_edi', this.changes.edi_dian_acquirer_email);

            // Update email - always replace when user clicks Replace button
            this.updateFieldValue('email', this.changes.edi_dian_acquirer_email);
        }
    },

    async getDianAcquirerAndReplace() {
        await this.getDianAcquirer();
        await this.acquirerReplace();
    },
});

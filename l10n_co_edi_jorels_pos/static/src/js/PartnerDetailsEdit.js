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

odoo.define('l10n_co_edi_jorels_pos.PartnerDetailsEdit', function(require) {
    'use strict';

    const {useState} = owl;
    const Registries = require('point_of_sale.Registries');
    const PartnerDetailsEdit = require('point_of_sale.PartnerDetailsEdit');

    const JPartnerDetailsEdit = (PartnerDetailsEdit) =>
        class extends PartnerDetailsEdit {
            setup() {
                super.setup();
                this.intFields.push(
                    'l10n_latam_identification_type_id',
                    'type_regime_id',
                    'type_liability_id',
                    'municipality_id'
                );
                const partner = this.props.partner;
                this.changes = useState({...this.changes,
                    company_type: partner.company_type,
                    l10n_latam_identification_type_id: partner.l10n_latam_identification_type_id && partner.l10n_latam_identification_type_id[0],
                    type_regime_id: partner.type_regime_id && partner.type_regime_id[0],
                    type_liability_id: partner.type_liability_id && partner.type_liability_id[0],
                    municipality_id: partner.municipality_id && partner.municipality_id[0],
                    email_edi: partner.email_edi || "",
                    edi_dian_acquirer_email: partner.edi_dian_acquirer_email,
                    edi_dian_acquirer_name: partner.edi_dian_acquirer_name,
                });
            }

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
            }

            async getDianAcquirer() {
                const vat = this.changes.vat || this.props.partner.vat;
                const l10nLatamTypeId = this.changes.l10n_latam_identification_type_id ||
                                       (this.props.partner.l10n_latam_identification_type_id && this.props.partner.l10n_latam_identification_type_id[0]);

                try {
                    const result = await this.rpc({
                        model: 'res.partner',
                        method: 'fetch_dian_acquirer_data_latam_type',
                        args: [l10nLatamTypeId, vat],
                        context: this.env.session.user_context,
                    });

                    if (result) {
                        this.updateFieldValue('edi_dian_acquirer_email', result.email || '');
                        this.updateFieldValue('edi_dian_acquirer_name', result.name || '');
                    }
                    else{
                        this.showPopup('ErrorPopup', {
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

                    this.showPopup('ErrorPopup', {
                        title: 'Error en consulta DIAN',
                        body: errorMessage,
                    });
                }
            }

            updateFieldValue(fieldName, value) {
                // Update the changes object
                this.changes[fieldName] = value;

                // Force update the DOM input/select element
                const fieldElement = this.el.querySelector(`[name="${fieldName}"]`);
                if (fieldElement) {
                    fieldElement.value = value;
                    // Trigger change event to ensure POS recognizes the change
                    fieldElement.dispatchEvent(new Event('change', { bubbles: true }));
                    fieldElement.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }

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

                    // Only update email if it's empty
                    const currentEmail = this.changes.email || this.props.partner.email;
                    if (!currentEmail) {
                        this.updateFieldValue('email', this.changes.edi_dian_acquirer_email);
                    }
                }
            }

            async getDianAcquirerAndReplace() {
                await this.getDianAcquirer();
                await this.acquirerReplace();
            }
        };

    Registries.Component.extend(PartnerDetailsEdit, JPartnerDetailsEdit);

    return PartnerDetailsEdit;
});
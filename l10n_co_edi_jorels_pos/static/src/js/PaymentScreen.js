/*
*   l10n_co_edi_jorels_pos
*   Copyright (C) 2022  Jorels SAS
*
*   This program is free software: you can redistribute it and/or modify
*   it under the terms of the GNU Affero General Public License as published
*   by the Free Software Foundation, either version 3 of the License, or
*   (at your option) any later version.
*
*   This program is distributed in the hope that it will be useful,
*   but WITHOUT ANY WARRANTY; without even the implied warranty of
*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*   GNU Affero General Public License for more details.
*
*   You should have received a copy of the GNU Affero General Public License
*   along with this program.  If not, see <https://www.gnu.org/licenses/>.
*
*   email: info@jorels.com
*
*/

odoo.define('l10n_co_edi_jorels_pos.PaymentScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const PaymentScreen = require('point_of_sale.PaymentScreen');

    const JPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
            }
            toggleIsToElectronicInvoice() {
                this.currentOrder.set_to_electronic_invoice(!this.currentOrder.is_to_electronic_invoice());
                this.render();
            }
            async _postPushOrderResolve(order, order_server_ids) {
                try {
                    if (order.is_to_invoice()) {
                        const result = await this.rpc({
                            model: 'pos.order',
                            method: 'get_invoice',
                            args: [order_server_ids],
                        }).then(function (invoice) {
                            return invoice;
                        });
                        order.set_invoice(result || null);
                    }
                } finally {
                    return super._postPushOrderResolve(...arguments);
                }
            }
        };

    Registries.Component.extend(PaymentScreen, JPaymentScreen);

    return PaymentScreen;
});
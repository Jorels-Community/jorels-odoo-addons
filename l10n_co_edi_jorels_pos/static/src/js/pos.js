// Jorels S.A.S. - Copyright (2019-2022)
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

odoo.define('l10n_co_edi_jorels_pos', function(require) {
    "use strict";

    var PosDB = require('point_of_sale.DB');
    var core = require('web.core');
    var exports = require('point_of_sale.models');
    var gui = require('point_of_sale.gui');
    var screens = require('point_of_sale.screens');
    var _t = core._t;
    var rpc = require('web.rpc');

    var models = exports.PosModel.prototype.models;

    var partner_fields = [
        'company_type',
        'l10n_co_document_type',
        'type_regime_id',
        'type_liability_id',
        'municipality_id',
        'email_edi'
    ];

    models.push(
        {
            model:  'l10n_co_edi_jorels.type_regimes',
            fields: ['name'],
            loaded: function(self, type_regimes) {
                self.type_regimes = type_regimes;
            }
        },
        {
            model:  'l10n_co_edi_jorels.type_liabilities',
            fields: ['name'],
            loaded: function(self, type_liabilities) {
                self.type_liabilities = type_liabilities;
            }
        },
        {
            model:  'l10n_co_edi_jorels.municipalities',
            fields: ['name'],
            loaded: function(self, municipalities) {
                self.municipalities = municipalities;
            }
        },
        // Por ahora solo se permiten contactos de Colombia
        // TODO: Dar soporte para otros paises
        {
            model:  'res.country.state',
            fields: ['name','country_id'],
            domain: [['country_id.name','=','Colombia']],
            loaded: function(self, states) {
                self.states = states;
            }
        },
    );

    var set_fields_to_model = function(fields, models) {
        for(var i = 0; i < models.length; i++) {
            if(models[i].model == 'res.partner') {
                var model = models[i];
                for(var j = 0; j < fields.length; j++){
                    model.fields.push(fields[j]);
                }
                var old_domain = model.domain;
                model.domain = function(self) {
                    return ['|', old_domain[0], ['id','=',self.company.partner_id[0]]];
                }

                var old_loaded = model.loaded;
                model.loaded = function(self, partners) {
                    for(var i = 0; i < partners.length; i++) {
                        if(partners[i].id == self.company.partner_id[0]) {
                            var company_partner = partners.splice(i, 1);
                            self.company_partner = company_partner;
                        }
                    }
                    old_loaded(self, partners);
                }
            }
        }
    }

    set_fields_to_model(partner_fields, models);

    screens.ClientListScreenWidget.include({
        display_client_details: function(visibility,partner,clickpos) {
            this._super(visibility,partner,clickpos);

            // Por ahora solo se permiten contactos de Colombia
            // TODO: Dar soporte para otros paises
            var country_select = $('.client-address-country');
            country_select.val("49");
            country_select.attr('disabled', true);
        },
    });

    screens.PaymentScreenWidget.include({
        finalize_validation: function () {
            var self = this;
            var order = this.pos.get_order();
            if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {

                this.pos.proxy.open_cashbox();
            }
            order.initialize_validation_date();
            order.finalized = true;
            if (order.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;

                invoiced.fail(this._handleFailedPushForInvoice.bind(this, order, false));

                invoiced.done(function (orderId) {
                    self.invoicing = false;
                    rpc.query({
                        model: 'pos.order',
                        method: 'get_invoice',
                        args: [orderId],
                    })
                    .then(function (invoice) {
                        var order = self.pos.get_order();
                        order.invoice = invoice;
                        self.gui.show_screen('receipt');
                    });
                });
            } else {
                this.pos.push_order(order);
                this.gui.show_screen('receipt');
            }
        },
        click_invoice: function(){
            var order = this.pos.get_order();
            order.set_to_invoice(!order.is_to_invoice());
            if (order.is_to_invoice()) {
                this.$('.js_invoice').addClass('highlight');
                this.$('.js_electronic_invoice').removeClass('hidden');
            } else {
                this.$('.js_invoice').removeClass('highlight');
                this.$('.js_electronic_invoice').addClass('hidden');
            }
        },
        click_electronic_invoice: function(){
            var order = this.pos.get_order();
            order.set_to_electronic_invoice(!order.is_to_electronic_invoice());
            if (order.is_to_electronic_invoice()) {
                this.$('.js_electronic_invoice').addClass('highlight');
            } else {
                this.$('.js_electronic_invoice').removeClass('highlight');
            }
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.js_electronic_invoice').click(function(){
                self.click_electronic_invoice();
            });
        },
    });

    exports.PosModel = exports.PosModel.extend({
        push_and_invoice_order: function (order) {
            var self = this;
            var invoiced = new $.Deferred();

            if (!order.get_client()) {
                invoiced.reject({ code: 400, message: 'Missing Customer', data: {} });
                return invoiced;
            }
            var order_id = this.db.add_order(order.export_as_JSON());

            this.flush_mutex.exec(function () {
                var done = new $.Deferred(); // holds the mutex

                // send the order to the server
                // we have a 30 seconds timeout on this push.
                // FIXME: if the server takes more than 30 seconds to accept the order,
                // the client will believe it wasn't successfully sent, and very bad
                // things will happen as a duplicate will be sent next time
                // so we must make sure the server detects and ignores duplicated orders

                var transfer = self._flush_orders([self.db.get_order(order_id)], { timeout: 30000, to_invoice: true });

                transfer.fail(function (error) {
                    invoiced.reject(error);
                    done.reject();
                });

                // on success, get the order id generated by the server
                transfer.pipe(function (order_server_id) {

                    // generate the pdf and download it
                    if (order_server_id.length) {
                        self.chrome.do_action('point_of_sale.pos_invoice_report', {
                            additional_context: {
                                active_ids: order_server_id,
                            }
                        }).done(function () {
                            invoiced.resolve(order_server_id);
                            done.resolve();
                        }).fail(function (error) {
                            invoiced.reject({ code: 401, message: 'Backend Invoice', data: { order: order } });
                            done.reject();
                        });
                    } else {
                        // The order has been pushed separately in batch when
                        // the connection came back.
                        // The user has to go to the backend to print the invoice
                        invoiced.reject({ code: 401, message: 'Backend Invoice', data: { order: order } });
                        done.reject();
                    }
                });
                return done;
            });
            return invoiced;
        },
        set_to_electronic_invoice: function(to_electronic_invoice) {
            this.to_electronic_invoice = to_electronic_invoice;
        },
        is_to_electronic_invoice: function(){
            return this.to_electronic_invoice;
        },
    });

    exports.Order = exports.Order.extend({
        init_from_JSON: function(json) {
            var client;
            this.sequence_number = json.sequence_number;
            this.pos.pos_session.sequence_number = Math.max(this.sequence_number+1,this.pos.pos_session.sequence_number);
            this.session_id = json.pos_session_id;
            this.uid = json.uid;
            this.name = _t("Order ") + this.uid;
            this.validation_date = json.creation_date;

            if (json.fiscal_position_id) {
                var fiscal_position = _.find(this.pos.fiscal_positions, function (fp) {
                    return fp.id === json.fiscal_position_id;
                });

                if (fiscal_position) {
                    this.fiscal_position = fiscal_position;
                } else {
                    console.error('ERROR: trying to load a fiscal position not available in the pos');
                }
            }

            if (json.pricelist_id) {
                this.pricelist = _.find(this.pos.pricelists, function (pricelist) {
                    return pricelist.id === json.pricelist_id;
                });
            } else {
                this.pricelist = this.pos.default_pricelist;
            }

            if (json.partner_id) {
                client = this.pos.db.get_partner_by_id(json.partner_id);
                if (!client) {
                    console.error('ERROR: trying to load a partner not available in the pos');
                }
            } else {
                client = null;
            }
            this.set_client(client);

            this.temporary = false;     // FIXME
            this.to_invoice = false;    // FIXME
            this.to_electronic_invoice = false;    // FIXME

            var orderlines = json.lines;
            for (var i = 0; i < orderlines.length; i++) {
                var orderline = orderlines[i][2];
                this.add_orderline(new exports.Orderline({}, {pos: this.pos, order: this, json: orderline}));
            }

            var paymentlines = json.statement_ids;
            for (var i = 0; i < paymentlines.length; i++) {
                var paymentline = paymentlines[i][2];
                var newpaymentline = new exports.Paymentline({},{pos: this.pos, order: this, json: paymentline});
                this.paymentlines.add(newpaymentline);

                if (i === paymentlines.length - 1) {
                    this.select_paymentline(newpaymentline);
                }
            }
        },
        export_as_JSON: function() {
            var orderLines, paymentLines;
            orderLines = [];
            this.orderlines.each(_.bind( function(item) {
                return orderLines.push([0, 0, item.export_as_JSON()]);
            }, this));
            paymentLines = [];
            this.paymentlines.each(_.bind( function(item) {
                return paymentLines.push([0, 0, item.export_as_JSON()]);
            }, this));
            return {
                name: this.get_name(),
                amount_paid: this.get_total_paid() - this.get_change(),
                amount_total: this.get_total_with_tax(),
                amount_tax: this.get_total_tax(),
                amount_return: this.get_change(),
                lines: orderLines,
                statement_ids: paymentLines,
                pos_session_id: this.pos_session_id,
                pricelist_id: this.pricelist ? this.pricelist.id : false,
                partner_id: this.get_client() ? this.get_client().id : false,
                user_id: this.pos.get_cashier().id,
                uid: this.uid,
                sequence_number: this.sequence_number,
                creation_date: this.validation_date || this.creation_date, // todo: rename creation_date in master
                fiscal_position_id: this.fiscal_position ? this.fiscal_position.id : false,
                to_invoice: this.to_invoice ? this.to_invoice : false,
                to_electronic_invoice: this.to_electronic_invoice ? this.to_electronic_invoice : false,
            };
        },
        set_to_electronic_invoice: function(to_electronic_invoice) {
            this.to_electronic_invoice = to_electronic_invoice;
        },
        is_to_electronic_invoice: function(){
            return this.to_electronic_invoice;
        },
    });

    screens.ReceiptScreenWidget.include({
		show: function () {
			this._super();
			var order = this.pos.get_order();
			if (order.invoice && order.invoice.ei_qr_data && order.invoice.ei_is_valid){
				new QRCode(document.getElementById("ei_qr_data") , {
					text: String(order.invoice.ei_qr_data),
					width: 100,
					height: 100
				});
			}
		},
	});

});

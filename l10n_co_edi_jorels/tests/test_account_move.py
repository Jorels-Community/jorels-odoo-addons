# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of l10n_co_edi_jorels.
#
# l10n_co_edi_jorels is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestAccountMove(TransactionCase):
    def setUp(self):
        super(TestAccountMove, self).setUp()
        self.partner = self.env['res.partner'].create({'name': 'Cliente de Prueba'})
        self.product1 = self.env['product.product'].create({'name': 'Producto 1', 'list_price': 100.0})
        self.product2 = self.env['product.product'].create({'name': 'Producto 2', 'list_price': 50.0})

        # Adding resolutions
        self.resolution_electronic_invoice = self.env['l10n_co_edi_jorels.resolution'].create({
            'resolution_api_sync': False,
            'resolution_type_document_id': 1,
            'resolution_prefix': 'SETP',
            'resolution_resolution': '1234567890',
            'resolution_resolution_date': '2024-01-01',
            'resolution_technical_key': 'qwerty1234567890',
            'resolution_from': '1',
            'resolution_to': '1000',
            'resolution_date_from': '2024-01-01',
            'resolution_date_to': '2025-01-01',
            'company_id': 1,
        })

        # Adding journal
        self.journal = self.env['account.journal'].search([('id', '=', 1)])
        self.journal.write({
            'resolution_invoice_id': self.resolution_electronic_invoice.id,
        })

        # Adding taxes
        self.tax_iva = self.env['account.tax'].create({
            'name': 'IVA Compra 19% (Test)',
            'description': 'IVA Compra 19% (Test)',
            'amount_type': 'percent',
            'amount': 19.0,
            'type_tax_use': 'sale',
            'edi_tax_id': 1,
            'dian_report_tax_base': 'auto',
        })

        self.tax_rtefte = self.env['account.tax'].create({
            'name': 'RteFte -2.50% Ventas (Test)',
            'description': 'RteFte -2.50% Ventas (Test)',
            'amount_type': 'percent',
            'amount': -2.5,
            'type_tax_use': 'sale',
            'edi_tax_id': 6,
            'dian_report_tax_base': 'auto',
        })

        self.tax_excluido = self.env['account.tax'].create({
            'name': 'IVA Excluido (Test)',
            'description': 'IVA Excluido (Test)',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'sale',
            'edi_tax_id': 1,
            'dian_report_tax_base': 'auto',
        })

        # Adding Trm rate, COP to USD
        self.env['res.currency.rate'].create({
            'name': datetime.now(),
            'currency_id': self.env.ref('base.USD').id,
            'rate': 0.000257,
        })

    def test_create_edi_co_move(self):
        # Adding invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'currency_id': self.env.ref('base.USD').id,
            'journal_id': self.journal.id,
        })

        # Adding invoice lines
        invoice.write({
            'invoice_line_ids': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'quantity': 2.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, [self.tax_excluido.id, self.tax_rtefte.id])],
                }),
                (0, 0, {
                    'name': self.product2.name,
                    'product_id': self.product2.id,
                    'quantity': 1.0,
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, [self.tax_iva.id, self.tax_rtefte.id])],
                })
            ]
        })

        # Check number of invoices
        invoices = self.env['account.move'].search([('partner_id', '=', self.partner.id)])
        self.assertEqual(len(invoices), 1)

        # Ckeck number of invoice lines
        self.assertEqual(len(invoice.invoice_line_ids), 2)

        # Check totals
        self.assertAlmostEqual(invoice.ei_amount_tax_withholding, -10.0)
        self.assertAlmostEqual(invoice.ei_amount_tax_withholding_company, -38910.51)

        self.assertAlmostEqual(invoice.ei_amount_tax_no_withholding, 38.0)
        self.assertAlmostEqual(invoice.ei_amount_tax_no_withholding_company, 147859.92)

        self.assertAlmostEqual(invoice.ei_amount_total_no_withholding, 438.0)
        self.assertAlmostEqual(invoice.ei_amount_total_no_withholding_company, 1704280.16)

        self.assertAlmostEqual(invoice.ei_amount_excluded, 200.0)
        self.assertAlmostEqual(invoice.ei_amount_excluded_company, 778210.12)

        self.assertAlmostEqual(invoice.amount_untaxed, 400.0)
        self.assertAlmostEqual(invoice.amount_untaxed_signed, 1556420.24)

        self.assertAlmostEqual(invoice.amount_total, 428.0)
        self.assertAlmostEqual(invoice.amount_total_signed, 1665369.65)

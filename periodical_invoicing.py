# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2014 Ozono informatica
# http://github.com/organizations/ozonoinformatica/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import orm, fields, osv
from datetime import datetime, timedelta
from addons import decimal_precision as dp
from tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class agreement(orm.Model):
    _name = 'account.periodical_invoicing.agreement'
    _inherit = 'account.periodical_invoicing.agreement'
    _description = "Set service date start/end for electronic invoices in argentina"

    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, readonly=False),
    }
    def _invoice_created(self, cr, uid, agreement, agreement_lines_invoiced, invoice_id, context={}):
        invoice_obj = self.pool.get('account.invoice')
        invoice = invoice_obj.browse(cr, uid, invoice_id)
        if invoice.afip_concept in ['2', '3']:
            (agreement_line, next_invoice_date) = agreement_lines_invoiced.items()[0]
            if agreement.period_type == 'pre-paid':
                from_date = next_invoice_date
                to_date = (self.__get_next_term_date(next_invoice_date,
                                                    agreement_line.invoicing_unit,
                                                    agreement_line.invoicing_interval) -
                                                    timedelta(days=1))
            else:
                from_date = self.__get_previous_term_date(next_invoice_date,
                                                    agreement_line.invoicing_unit,
                                                    agreement_line.invoicing_interval)
                to_date = next_invoice_date - timedelta(days=1)

            ids = [invoice_id]
            invoice_values = {
                              'afip_service_start': from_date,
                              'afip_service_end': to_date,
                              'journal_id': agreement.journal_id.id,
            }
            invoice_obj.write(cr, uid, ids, invoice_values, context=context)

    def create_invoice(self, cr, uid, agreement, agreement_lines, context={}):
        """
        Method that creates an invoice from given data.
        @param agreement: Agreement from which invoice is going to be generated.
        @param agreement_lines: Dictionary with agreement lines as keys and next invoice date of that line as values.
        """
        now = datetime.now()
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        lang_obj = self.pool.get('res.lang')
        # Get lang record for format purposes
        lang_ids = lang_obj.search(cr, uid, [('code', '=', agreement.partner_id.lang)])
        lang = lang_obj.browse(cr, uid, lang_ids)[0]
        # Create invoice object
        context['company_id'] = agreement.company_id.id
        context['force_company'] = agreement.company_id.id
        context['type'] = 'out_invoice'
        invoice = {
            'date_invoice': now.strftime('%Y-%m-%d'),
            'origin': agreement.number,
            'partner_id': agreement.partner_id.id,
            'journal_id': invoice_obj._get_journal(cr, uid, context),
            'type': 'out_invoice',
            'state': 'draft',
            'currency_id': invoice_obj._get_currency(cr, uid, context),
            'company_id': agreement.company_id.id,
            'reference_type': 'none',
            'check_total': 0.0,
            'internal_number': False,
            'user_id': agreement.partner_id.user_id.id,
        }
        # Get other invoice values from agreement partner
        invoice.update(invoice_obj.onchange_partner_id(cr, uid, [],
                type=invoice['type'], partner_id=agreement.partner_id.id,
                company_id=agreement.company_id.id)['value'])
        # Prepare invoice lines objects
        agreement_lines_ids = []
        invoice_lines = []
        for agreement_line in agreement_lines.keys():
            invoice_line = {
                'product_id': agreement_line.product_id.id,
                'quantity': agreement_line.quantity,
                'discount': agreement_line.discount,
            }
            _logger.warning("impuesto: " + str(agreement_line.agreement_line_tax_id))
            # get other invoice line values from agreement line product
            invoice_line.update(invoice_line_obj.product_id_change(cr, uid, [],
                    product=agreement_line.product_id.id, uom_id=False,
                    qty=agreement_line.quantity,
                    partner_id=agreement.partner_id.id,
                    fposition_id=invoice['fiscal_position'],
                    context=context)['value'])
            if agreement_line.price > 0:
                invoice_line['price_unit'] = agreement_line.price
            # Put line taxes
            #invoice_line['invoice_line_tax_id'] = [(6, 0, tuple(invoice_line['invoice_line_tax_id']))]
            # Put custom description

            invoice_tax = []
            for tax in agreement_line.agreement_line_tax_id:
                invoice_tax.append(tax.id)

            #_logger.info("ids impuesto: " + str(invoice_tax))
            invoice_line['invoice_line_tax_id'] = [(6, 0, invoice_tax)]
            #_logger.warning("impuesto linea luego: " + str(invoice_line['invoice_line_tax_id']))

            if agreement_line.additional_description:
                invoice_line['name'] += " " + agreement_line.additional_description
            # Put period string
            next_invoice_date = agreement_lines[agreement_line]
            if agreement.period_type == 'pre-paid':
                from_date = next_invoice_date
                to_date = (self.__get_next_term_date(next_invoice_date,
                                        agreement_line.invoicing_unit,
                                        agreement_line.invoicing_interval) -
                                        timedelta(days=1))
            else:
                from_date = self.__get_previous_term_date(next_invoice_date,
                                            agreement_line.invoicing_unit,
                                            agreement_line.invoicing_interval)
                to_date = next_invoice_date - timedelta(days=1)
            invoice_line['name'] += "\n" + _('Period: from %s to %s') %(
                                        from_date.strftime(lang.date_format),
                                        to_date.strftime(lang.date_format))
            invoice_lines.append(invoice_line)
            _logger.warning("impuesto linea luego: " + str(invoice_line['invoice_line_tax_id']))

            agreement_lines_ids.append(agreement_line.id)
        # Add lines to invoice and create it
        invoice['invoice_line'] = [(0, 0, x) for x in invoice_lines]
        invoice_id = invoice_obj.create(cr, uid, invoice, context=context)
        # Update last invoice date for lines
        self.pool.get('account.periodical_invoicing.agreement.line').write(cr, uid, agreement_lines_ids, {'last_invoice_date': now.strftime('%Y-%m-%d')} ,context=context)
        # Update agreement state
        if agreement.state != 'invoices':
            self.pool.get('account.periodical_invoicing.agreement').write(cr, uid, [agreement.id], {'state': 'invoices'} ,context=context)
        # Create invoice agreement record
        agreement_invoice = {
            'agreement_id': agreement.id,
            'date': now.strftime('%Y-%m-%d'),
            'invoice_id': invoice_id
        }
        self.pool.get('account.periodical_invoicing.agreement.invoice').create(cr, uid, agreement_invoice, context=context)
        return invoice_id

    def make_invoices_planned(self, cr, uid, context={}):
        return super(agreement, self).make_invoices_planned(cr, uid, context=context)

    def onchange_partner_id(self, cr, uid, ids, partner_id, company_id=False):
        # result = super(agreement,self).onchange_partner_id(cr, uid, ids,
        #               partner_id, company_id)
        result = {'value': {}}
        # Damos por sentado que es una factura de venta
        tipo = 'out_invoice'
        if company_id and partner_id:
            # Set list of valid journals by partner responsability
            partner_obj = self.pool.get('res.partner')
            company_obj = self.pool.get('res.company')
            partner = partner_obj.browse(cr, uid, partner_id)
            company = company_obj.browse(cr, uid, company_id)
            responsability = partner.responsability_id
            if responsability.issuer_relation_ids is None:
                return result

            # document_class_set = set([ i.document_class_id.id for i in responsability.issuer_relation_ids ])


            type_map = {
                'out_invoice': ['sale'],
                'out_refund': ['sale_refund'],
                'in_invoice': ['purchase'],
                'in_refund': ['purchase_refund'],
            }

            if not company.partner_id:
                result['warning'] = {'title': _('Your company has not setted any partner'),
                                   'message': _('That\'s is really strange. You must have a partner associated to your company.')}
                # _logger.warning('Your company "%s" has not setted any partner.' % company.name)
                return result

            if not company.partner_id.responsability_id.id:
                result['warning'] = {'title': _('Your company has not setted any responsability'),
                                   'message': _('Please, set your company responsability in the company partner before continue.')}
                # _logger.warning('Your company "%s" has not setted any responsability.' % company.name)
                return result

            cr.execute("""
                       SELECT DISTINCT J.id, J.name, IRSEQ.number_next
                       FROM account_journal J
                       LEFT join ir_sequence IRSEQ on (J.sequence_id = IRSEQ.id)
                       LEFT join afip_journal_class JC on (J.journal_class_id = JC.id)
                       LEFT join afip_document_class DC on (JC.document_class_id = DC.id)
                       LEFT join afip_responsability_relation RR on (DC.id = RR.document_class_id)
                       WHERE
                       (RR.id is Null OR (RR.id is not Null AND RR.issuer_id = %s AND RR.receptor_id = %s)) AND
                       J.type in %s AND
                       J.id is not NULL AND
                       J.sequence_id is not NULL
                       AND IRSEQ.number_next is not NULL
                       ORDER BY IRSEQ.number_next DESC;
                      """, (company.partner_id.responsability_id.id, partner.responsability_id.id, tuple(type_map[tipo])))
            accepted_journal_ids = [ x[0] for x in cr.fetchall() ]

            if 'domain' not in result: result['domain'] = {}
            if 'value' not in result: result['value'] = {}

            if accepted_journal_ids:
                result['domain'].update({
                    'journal_id': [('id', 'in', accepted_journal_ids)],
                })
                result['value'].update({
                    'journal_id': accepted_journal_ids[0],
                })
            else:
                result['domain'].update({
                    'journal_id': [('id', 'in', [])],
                })
                result['value'].update({
                    'journal_id': False,
                })

        return result

class agreement_line(osv.osv):
    _inherit = 'account.periodical_invoicing.agreement.line'
    _description = "Add optional tax for agreement lines"
    _name = 'account.periodical_invoicing.agreement.line'

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        invoice_obj = self.pool.get('account.invoice')
        cur = cur_obj.browse(cr, uid, invoice_obj._get_currency(cr, uid, context))

        for line in self.browse(cr, uid, ids):
            price = line.price * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.agreement_line_tax_id, price, line.quantity, product=line.product_id, partner=line.agreement_id.partner_id)
            total_tax = 0
            for tax in taxes['taxes']:
                total_tax = total_tax + tax['amount']
            res[line.id] = taxes['total'] + total_tax

            if line.agreement_id:
                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    _columns = {
        'agreement_line_tax_id': fields.many2many('account.tax', 'agreement_line_tax', 'agreement_line_id', 'tax_id', 'Impuestos', domain=[('parent_id', '=', False)]),
        'price_subtotal': fields.function(_amount_line, string='Total', type="float", method=True,
            digits_compute= dp.get_precision('Account')),
        }


# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2014 OpenERP - Ozono informatica.
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
{
	'name':	 'Facturacion periodica con facturacion electronica',
	'version':  '1.0',
	'author':   'Ozono informatica',
	'category': 'Argentina',
	'website':  'www.ozonoinformatica.com.ar',
	'license':  'AGPL-3',
	'description': """
Extension del modulo de facturacion periodica para que indique, en caso de factura por servicios, el periodo
en el cual se realizo dicho trabajo. Estos valores son necesarios para la facturacion electronica de Argentina.
Tambien permite indicar el diario para el cual se va a crear la factura, y la posibilidad de indicar los impuestos
para los productos a facturar.
""",
	'depends': [
        'account_periodical_invoicing',
        'l10n_ar_wsafip_fe',
	],
	'init_xml': [],
	'demo_xml': [],
	'test': [],
	'data': ['periodical_invoicing_view.xml',],
	'update_xml': [],
	'active': False,
	'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

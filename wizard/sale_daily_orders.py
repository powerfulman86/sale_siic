# -*- coding: utf-8 -*-

from odoo.tools import date_utils
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class SaleDailyOrders(models.TransientModel):
    _name = "sale.daily.order"
    _description = "Sales Daily Orders"

    @api.model
    def _get_branch(self):
        if self.env.user.branch_id:
            return self.env.user.branch_id.id
        else:
            return self.env['res.branch'].search([], limit=1, order='id').id

    @api.model
    def _get_warehouse(self):
        if self.env.user.branch_id:
            return self.env['stock.warehouse'].search([('branch_id', '=', self.env.user.branch_id.id)], limit=1,
                                                      order='id').id
        else:
            return self.env['stock.warehouse'].search([], limit=1, order='id').id

    from_date = fields.Date(string="Start Date", default=fields.Date.today(), reqired=True)
    to_date = fields.Date(string="End Date", default=fields.Date.today(), reqired=True)
    order_source = fields.Selection(string="Order Source",
                                    selection=[('all', 'ALL'),
                                               ('default', 'Default'),
                                               ('sugar', 'Sugar'),
                                               ('wood', 'Wood'),
                                               ('moulas', 'Moulas'), ], default='all', )
    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch", help='This is branch to set',
                                default=_get_branch)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   domain="['|',('branch_id', '=', branch_id),('branch_id','=',False)]",
                                   default=_get_warehouse)
    status = fields.Selection([('all', 'All'),
                               ('draft', 'Draft'),
                               ('done', 'Done'),
                               ('ondelivery', 'On Delivery'),
                               ('close', 'Closed'), ],
                              string='Status', default='all', reqired=True)
    company_ids = fields.Many2many('res.company', string='Companies')
    customer_ids = fields.Many2many('res.partner', string="Customers", )
    product_ids = fields.Many2many('product.product', string='Products')

    @api.onchange('branch_id')
    def _branch_reset_warehouse(self):
        self.update({'warehouse_id': False, })

    def get_sale_daily_report(self):
        datas = self._get_data()
        return self.env.ref('sale_siic.action_sale_daily_report').report_action([], data=datas)

    def _get_data(self):
        # apply status role and source rule
        if self.warehouse_id:
            if self.order_source == 'all':
                if self.status == 'all':
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id),
                         ('order_id.warehouse_id', '=', self.warehouse_id.id)])
                else:
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id),
                         ('order_id.warehouse_id', '=', self.warehouse_id.id),
                         ('order_id.state', '=', self.status)])
            else:
                if self.status == 'all':
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id),
                         ('order_id.warehouse_id', '=', self.warehouse_id.id),
                         ('order_id.order_source', '=', self.order_source)])
                else:
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id),
                         ('order_id.warehouse_id', '=', self.warehouse_id.id),
                         ('order_id.state', '=', self.status),
                         ('order_id.order_source', '=', self.order_source)])
        else:
            if self.order_source == 'all':
                if self.status == 'all':
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id)])
                else:
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id),
                         ('order_id.state', '=', self.status)])
            else:
                if self.status == 'all':
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id),
                         ('order_id.order_source', '=', self.order_source)])
                else:
                    sale_order_line = self.env['sale.order.line'].search(
                        [('order_id.branch_id', '=', self.branch_id.id),
                         ('order_id.state', '=', self.status),
                         ('order_id.order_source', '=', self.order_source)])

        filtered = self._get_filtered(sale_order_line)
        result = []
        customers = []
        products = []
        for rec in self.customer_ids:
            a = {'id': rec, 'name': rec.name}
            customers.append(a)
        for rec in self.product_ids:
            a = {'id': rec, 'name': rec.name}
            products.append(a)

        # append data
        for so in filtered:
            res = {
                'so': so.order_id.name,
                'date': so.order_id.date_order,
                'product': so.product_id.display_name,
                'quantity': so.product_uom_qty,
                'partner': so.order_id.partner_id.name,
                'partner_shipping_id': so.order_id.partner_shipping_id.name,
                'delivery_receipt_number': so.order_id.delivery_receipt_number,
                'delivery_vehicle': so.order_id.delivery_vehicle,
                'delivery_truck': so.order_id.delivery_truck,
                'state': so.order_id.state,
                'sale_contract': so.order_id.sale_contract.internal_reference,
            }
            result.append(res)
        result.sort(key=lambda b: (b['date'], b['delivery_receipt_number']))

        datas = {
            'ids': self,
            'model': 'sale.daily.order',
            'form': result,
            'partner_id': customers,
            'product_id': products,
            'start_date': self.from_date,
            'end_date': self.to_date,
            'status': self.status,
            'branch_id': self.branch_id.name,
            'warehouse_id': self.warehouse_id.name,
            'order_source': self.order_source,
            'no_value': False,
            'same_date': False,

        }
        if self.from_date and self.to_date and not self.customer_ids and not self.product_ids:
            datas['no_value'] = True
        if self.from_date == self.to_date:
            datas['same_date'] = True
        return datas

    def _get_filtered(self, sale_order_line):
        if self.from_date and self.to_date and self.company_ids:
            filtered = list(filter(lambda
                                       x: self.from_date <= x.order_id.date_order.date() <= self.to_date and x.order_id.company_id in self.company_ids,
                                   sale_order_line))
        elif not self.from_date and self.to_date and self.company_ids:
            filtered = list(filter(lambda
                                       x: x.order_id.date_order.date() <= self.to_date and x.order_id.company_id in self.company_ids,
                                   sale_order_line))
        elif self.from_date and not self.to_date and self.company_ids:
            filtered = list(filter(lambda
                                       x: self.from_date >= x.order_id.date_order.date() and x.order_id.company_id in self.company_ids,
                                   sale_order_line))
        elif self.from_date and self.to_date and not self.company_ids:
            filtered = list(filter(lambda x: self.from_date <= x.order_id.date_order.date() <= self.to_date,
                                   sale_order_line))
        elif not self.from_date and not self.to_date and self.company_ids:
            filtered = list(filter(lambda x: x.order_id.company_id in self.company_ids, sale_order_line))
        elif not self.from_date and self.to_date and not self.company_ids:
            filtered = list(filter(lambda x: x.order_id.date_order.date() <= self.to_date, sale_order_line))
        elif self.from_date and not self.to_date and not self.company_ids:
            filtered = list(filter(lambda x: self.from_date >= x.order_id.date_order.date(), sale_order_line))
        else:
            filtered = sale_order_line

        return filtered

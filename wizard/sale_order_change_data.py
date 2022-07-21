# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderChangeDeliveryNumber(models.TransientModel):
    _name = "sale.order.change.delivery.number"
    _description = "Change Delivery Number"

    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch", readonly=True,)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, )
    order_source = fields.Selection(string="Order Source",
                                    selection=[('default', 'Default'), ('sugar', 'Sugar'), ('wood', 'Wood'),
                                               ('moulas', 'Moulas'), ],
                                    readonly=True, )
    new_receipt_number = fields.Char(string="Delivery Number", tracking=3, )

    sale_contract = fields.Many2one('sale.contract', "Sale Contract",
                                    domain="[('state', '=', 'progress'),"
                                           "('contract_source','=',order_source),"
                                           "('branch_id','=',branch_id),"
                                           "('partner_id','=',partner_id)]", )

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderChangeDeliveryNumber, self).default_get(fields)

        if 'active_model' in self._context:
            sale_order_id = self.env['sale.order'].browse(self._context.get('active_id'))
            if 'branch_id' in fields and 'branch_id' not in res:
                res['branch_id'] = sale_order_id.branch_id.id
            if 'partner_id' in fields and 'partner_id' not in res:
                res['partner_id'] = sale_order_id.partner_id.id
            if 'order_source' in fields and 'order_source' not in res:
                res['order_source'] = sale_order_id.order_source
        return res

    def change_delivery_number(self):
        self.ensure_one()
        sale_order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        sale_order_id.write({'delivery_receipt_number': self.new_receipt_number, })
        return {'type': 'ir.actions.act_window_close'}

    def change_sale_contract(self):
        self.ensure_one()
        sale_order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        sale_order_id.write({'sale_contract': self.sale_contract, })
        return {'type': 'ir.actions.act_window_close'}

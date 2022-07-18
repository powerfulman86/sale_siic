# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderChangeDeliveryNumber(models.TransientModel):
    _name = "sale.order.change.delivery.number"
    _description = "Change Delivery Number"

    new_receipt_number = fields.Char(string="Delivery Number", tracking=3, )

    def change_delivery_number(self):
        self.ensure_one()
        sale_order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        sale_order_id.write({'delivery_receipt_number': self.new_receipt_number, })
        return {'type': 'ir.actions.act_window_close'}

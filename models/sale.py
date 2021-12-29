# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += (line.product_uom_qty * line.price_unit) * (line.discount / 100)
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount': amount_discount,
                'amount_total': amount_untaxed + amount_tax,
            })

    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], string='Discount type',
                                     readonly=True,
                                     states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                     default='percent')
    discount_rate = fields.Float('Discount Rate', digits=dp.get_precision('Account'),
                                 readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    discount_extra_value = fields.Integer(string="Discount Extra", digits=dp.get_precision('Account'), )
    discount_commercial_value = fields.Integer(string="Discount Commercial", digits=dp.get_precision('Account'))

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all',
                                 track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_amount_all',
                                      digits=dp.get_precision('Account'), track_visibility='always')
    internal_reference = fields.Char(string="Order Number", required=True, states={'draft': [('readonly', False)]})
    order_type = fields.Selection(string="Type", selection=[('in', 'Local'), ('out', 'Foreign'), ], required=True,
                                  tracking=1, default='in')
    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch", required=True,
                                index=True, help='This is branch to set')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sale', 'Sale'),
        ('approved', 'Approved'),
        ('sent', 'Quotation Sent'),
        ('ondelivery', 'On Delivery'),
        ('delivered', 'Delivered'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    delivery_company = fields.Many2one(comodel_name="res.partner", string="Delivery Company", required=False,
                                       domain="[('delivery_company','=',True)]",
                                       states={'draft': [('readonly', False)]})

    receipt_date = fields.Datetime('Receipt Date', states={'draft': [('readonly', False)]},
                                   copy=False, readonly=True, )
    delivery_receipt_number = fields.Char(string="Receipt Number", states={'draft': [('readonly', False)]})
    delivery_vehicle = fields.Many2one(comodel_name="sale.delivery.vehicle", string="Delivery Vehicle", required=False,
                                       domain="[('partner_id','=','delivery_company')]",
                                       states={'draft': [('readonly', False)]})

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            else:
                total = discount = 0.0
                for line in order.order_line:
                    total += round((line.product_uom_qty * line.price_unit))
                if order.discount_rate != 0:
                    discount = (order.discount_rate / total) * 100
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount

    def _prepare_invoice(self, ):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
        })
        return invoice_vals

    def button_dummy(self):
        self.supply_rate()
        return True

    @api.constrains('internal_reference')
    def constrains_internal_reference(self):
        for rec in self:
            if not rec.internal_reference.isdigit():
                raise ValidationError(_("Order Number Must Be In Digits"))


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Account'), default=0.0)

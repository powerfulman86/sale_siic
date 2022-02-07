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
    discount_extra_value = fields.Integer(string="Discount Extra", digits=dp.get_precision('Account'), readonly=True,
                                          states={'draft': [('readonly', False)]})
    discount_commercial_value = fields.Integer(string="Discount Commercial", digits=dp.get_precision('Account'),
                                               readonly=True, states={'draft': [('readonly', False)]})

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all',
                                 track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_amount_all',
                                      digits=dp.get_precision('Account'), track_visibility='always')
    internal_reference = fields.Char(string="Order Number", required=True, readonly=True,
                                     states={'draft': [('readonly', False)]})
    order_type = fields.Selection(string="Type", selection=[('in', 'Local'), ('out', 'Foreign'), ], required=True,
                                  readonly=True, tracking=1, default='in', states={'draft': [('readonly', False)]})
    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch", required=True, readonly=True,
                                index=True, help='This is branch to set', states={'draft': [('readonly', False)]})

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sale', 'Sale'),
        ('sent', 'Quotation Sent'),
        ('done', 'Done'),
        ('ondelivery', 'On Delivery'),
        ('close', 'Closed'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    delivery_company = fields.Many2one(comodel_name="res.partner", string="Delivery Company", required=False,
                                       domain="[('delivery_company','=',True)]", readonly=True,
                                       states={'ondelivery': [('readonly', False)]})

    delivery_date = fields.Datetime('Delivered Date', states={'ondelivery': [('readonly', False)]},
                                    copy=False, readonly=True, )
    delivery_receipt_number = fields.Char(string="Delivery Number", readonly=True,
                                          states={'draft': [('readonly', False)]})
    delivery_voucher = fields.Char(string="Delivery Voucher", readonly=True,
                                   states={'ondelivery': [('readonly', False)]})
    delivery_vehicle = fields.Char(string="Delivery Vehicle", readonly=True, required=False,
                                   states={'draft': [('readonly', False)]})
    delivery_truck = fields.Char(string="Delivery Truck", readonly=True, required=False,
                                 states={'draft': [('readonly', False)]})
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        domain="[('parent_id', '=', partner_id),('type','=','delivery')]", )
    shipping_date = fields.Datetime('Shipping Date', states={'ondelivery': [('readonly', False)]},
                                    copy=False, readonly=True, )
    actual_shipping_id = fields.Many2one(
        'res.partner', string='Actual Shipping Address', readonly=True, required=True,
        states={'draft': [('readonly', False)]}, domain="[('type','=','delivery')]", )

    sale_contract = fields.Many2one('sale.contract', "Sale Contract", required=False, readonly=True,
                                    domain="[('state', '=', 'progress')]", states={'draft': [('readonly', False)]})

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=True,
                                   states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, )

    order_source = fields.Selection(string="Order Source", selection=[('default', 'Default'), ('sugar', 'Sugar'), ],
                                    required=False, default='default')

    def action_ondelivery(self):
        if not self.user_has_groups('sales_team.group_sale_manager'):
            return
        if self.state != 'done':
            return
        self.state = 'ondelivery'

    def action_close(self):
        if self.order_source == 'sugar':
            if not (self.delivery_date or self.delivery_voucher or self.delivery_company or self.actual_shipping_id):
                raise ValidationError(_("Delivery Data Must Be Completed Before Close !"))

        if self.partner_shipping_id.parent_id != self.actual_shipping_id.parent_id:
            # check if address changed
            raise ValidationError(_("Delivery Address Is Differ From Original Address !"))

        self.state = 'close'

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

    # @api.constraints('delivery_vehicle')
    # def check_vehicle_status(self):
    #     return

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

    def action_confirm(self):
        if not self.user_has_groups('sales_team.group_sale_manager'):
            return

        for rec in self:
            date = rec.date_order
            if len(rec.order_line.ids) == 0:
                raise ValidationError(_('You Must Add Products Data.'))

            res = super(SaleOrder, rec).action_confirm()
            rec.date_order = date
            return res

    def _cron_update_sale_status(self):
        orders = self.env['sale.order'].search[('order_source', '=', 'sugar'), ('state', '=', 'draft')]
        for rec in orders:
            rec.action_confirm()
            rec.action_ondelivery()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Account'), default=0.0)
    sale_contract = fields.Many2one(related='order_id.sale_contract', store=True, string='Sale Contract',
                                    readonly=False)
    contract_line_id = fields.Many2one('sale.contract.line', 'Contract details Lines', ondelete='set null', index=True,
                                       copy=False)

    def _copy_data_extend_business_fields(self, values):
        # OVERRIDE to copy the 'contract_line_id' field as well.
        super(SaleOrderLine, self)._copy_data_extend_business_fields(values)
        values['contract_line_id'] = self.contract_line_id.id

    @api.depends('product_id', 'sale_contract')
    def _get_sale_contract_line(self):
        self.ensure_one()

        contract_line = self.env['sale.contract.line'].search(
            [('contract_id.id', '=', self.sale_contract.id),
             ('product_id.id', '=', self.product_id.id)])

        if len(contract_line.ids) != 0:
            self.contract_line_id.id = contract_line.id

        # super(SaleOrderLine, self).onchange_product_id()
        # template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        # self.note = template.note or self.note

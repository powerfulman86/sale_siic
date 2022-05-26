# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from datetime import date, datetime, timedelta


class SaleContract(models.Model):
    _name = 'sale.contract'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Sales Contract"
    _rec_name = 'internal_reference'
    _order = 'date_contract desc, id desc'

    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    @api.model
    def _get_branch(self):
        if self.env.user.branch_id:
            return self.env.user.branch_id.id
        else:
            return self.env['res.branch'].search([], limit=1, order='id').id

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    internal_reference = fields.Char(string="Contract Number", required=True, readonly=True,
                                     states={'draft': [('readonly', False)]})
    name = fields.Char(string='Contact Reference', copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('progress', 'In Progress'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    date_contract = fields.Datetime(string='Contract Date', required=True, readonly=True, index=True,
                                    states={'draft': [('readonly', False)]}, copy=False,
                                    default=fields.Datetime.now, )
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True,
                                  help="Date on which sales order is created.")
    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, tracking=2, default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id)], readonly=True,
        states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True,
                                  required=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms', check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    contract_line = fields.One2many('sale.contract.line', 'contract_id', string='Contract Lines', readonly=True,
                                    states={'draft': [('readonly', False)]}, copy=True, auto_join=True)
    note = fields.Text('Terms and conditions', )
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=5)
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group',
                                    help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', tracking=4)
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True,
                                 digits=(12, 6), readonly=True,
                                 help='The rate of the currency to the currency of rate 1 applicable at the date of the order')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch", required=True, readonly=True, tracking=1,
                                index=True, help='This is branch to set', states={'draft': [('readonly', False)]},
                                default=_get_branch)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=True,
                                   domain="['|',('branch_id', '=', branch_id),('branch_id','=',False)]",
                                   states={'draft': [('readonly', False)]}, )
    team_id = fields.Many2one(
        'crm.team', 'Sales Team', readonly=True, states={'draft': [('readonly', False)]},
        change_default=True, default=_get_default_team, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    orders_ids = fields.One2many('sale.order', 'sale_contract', string='Orders')
    orders_count = fields.Integer(string='Orders Count', compute='_compute_order_ids')
    contract_source = fields.Selection(string="Contract Source", readonly=True, states={'draft': [('readonly', False)]},
                                       selection=[('default', 'Default'), ('sugar', 'Sugar'), ('wood', 'Wood'), ],
                                       required=True, default='default')
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True,
                                          states={'draft': [('readonly', False)]},
                                          domain="[('parent_id', '=', partner_id),('type','=','delivery')]", )
    shipping_type = fields.Selection(string="Shipping Type", readonly=True, states={'draft': [('readonly', False)]},
                                     selection=[('bycompany', 'By Company'), ('byclient', 'By Client'),
                                                ('noshipping', 'No Shipping'), ], required=True, default='bycompany')

    _sql_constraints = [
        ("contract_reference_uniq", "unique (internal_reference)", "Contract Number already exists !"),
    ]

    @api.depends('orders_ids')
    def _compute_order_ids(self):
        for contract in self:
            contract.orders_count = len(contract.orders_ids)

    def name_get(self):
        res = []
        for contract in self:
            name = contract.name
            if contract.partner_id.name:
                name = '[%s]-[%s] %s' % (contract.name, contract.internal_reference, contract.partner_id.name)
            res.append((contract.id, name))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        domain = expression.AND([
            args or [],
            ['|', '|', ('name', operator, name),
             ('internal_reference', operator, name),
             ('partner_id.name', operator, name)]
        ])
        order_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(order_ids).with_user(name_get_uid))

    @api.depends('contract_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.contract_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('pricelist_id', 'date_contract', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            if not order.company_id:
                order.currency_rate = order.currency_id.with_context(date=order.date_contract).rate or 1.0
                continue
            elif order.company_id.currency_id and order.currency_id:  # the following crashes if any one is undefined
                order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id,
                                                                                    order.currency_id, order.company_id,
                                                                                    order.date_contract)
            else:
                order.currency_rate = 1.0

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        partner_shipping = self.partner_id.shipping_type
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.uid
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id
        if partner_shipping:
            values['shipping_type'] = partner_shipping
        self.update(values)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.contract') or _('New')

            # Makes sure 'pricelist_id' are defined
            if any(f not in vals for f in ['pricelist_id']):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                vals['pricelist_id'] = vals.setdefault('pricelist_id',
                                                       partner.property_product_pricelist and partner.property_product_pricelist.id)

        if 'warehouse_id' not in vals and 'company_id' in vals and vals.get('company_id') != self.env.company.id:
            vals['warehouse_id'] = self.env['stock.warehouse'].search([('company_id', '=', vals.get('company_id'))],
                                                                      limit=1).id

        return super(SaleContract, self).create(vals)

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(
                    _('You can not delete a sent quotation or a confirmed sales order. You must first cancel it.'))
        return super(SaleContract, self).unlink()

    def action_view_sale_orders(self):
        self.ensure_one()
        # action = self.env.ref('sale.view_order_tree').read()[0]
        return {
            'name': _('Contract Sales Orders'),
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form,pivot',
            'domain': [('sale_contract', '=', self.id)],
            # 'context': {"default_sale_contract": self.id, },
        }

    def action_approve(self):
        for rec in self:
            if rec.state == 'draft':
                self.write({'state': 'approved'})

    def action_progress(self):
        for rec in self:
            if rec.state == 'approved':
                self.write({'state': 'progress'})

    def action_done(self):
        for rec in self:
            if rec.state == 'progress':
                self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def create_order(self):
        ship_id = self.partner_shipping_id.id
        if self.partner_shipping_id.id:
            sale_id = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'partner_shipping_id': ship_id,
                'internal_reference': 1234,
                'branch_id': self.branch_id.id,
                'date_order': date.today(),
                'origin': self.name,
                'sale_contract': self.id,
                'shipping_type': self.shipping_type,
                'warehouse_id': self.warehouse_id.id,
                'order_source': self.contract_source,
                'order_type': 'in',
                'pricelist_id': self.pricelist_id.id,
            })
        else:
            sale_id = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'internal_reference': 1234,
                'branch_id': self.branch_id.id,
                'date_order': date.today(),
                'origin': self.name,
                'sale_contract': self.id,
                'shipping_type': self.shipping_type,
                'warehouse_id': self.warehouse_id.id,
                'order_source': self.contract_source,
                'order_type': 'in',
                'pricelist_id': self.pricelist_id.id,
            })

        for line in self.contract_line:
            self.env['sale.order.line'].create({
                'order_id': sale_id.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_uom': line.product_uom.id,
                'price_unit': line.price_unit,
                'product_uom_qty': line.product_uom_qty,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', '=', sale_id.id)],
            'context': {'create': False},
        }

    def _cron_update_contract_status(self):
        # 1st update related contract line
        sales_check = self.env['sale.order.line'].search(
            [('sale_contract', '!=', False),
             ('contract_line_id', '=', False)])
        if sales_check.ids != 0:
            for line in sales_check:
                sale_contract_line = self.env['sale.contract.line'].search(
                    [('contract_id', '=', line.sale_contract.id),
                     ('product_id', '=', line.product_id.id),
                     ])
                if sale_contract_line.ids != 0:
                    line.contract_line_id = sale_contract_line


class SaleContractLine(models.Model):
    _name = 'sale.contract.line'
    _description = 'Sales Contract Line'
    _order = 'contract_id, sequence, id'
    _check_company_auto = True

    contract_id = fields.Many2one('sale.contract', string='Order Reference', required=True, ondelete='cascade',
                                  index=True,
                                  copy=False)
    name = fields.Text(string='Description', )
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one(
        'product.product', string='Product',
        domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
    product_template_id = fields.Many2one(
        'product.template', string='Product Template',
        related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)])
    product_updatable = fields.Boolean(string='Can Edit Product', readonly=True, default=True)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    product_custom_attribute_value_ids = fields.One2many('product.attribute.custom.value', 'sale_order_line_id',
                                                         string="Custom Values", copy=True)
    product_no_variant_attribute_value_ids = fields.Many2many('product.template.attribute.value', string="Extra Values",
                                                              ondelete='restrict')
    currency_id = fields.Many2one(related='contract_id.currency_id', depends=['contract_id.currency_id'], store=True,
                                  string='Currency', readonly=True)
    company_id = fields.Many2one(related='contract_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    partner_id = fields.Many2one(related='contract_id.partner_id', store=True, string='Customer', readonly=False)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('progress', 'In Progress'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], related='contract_id.state', string='Contract Status', readonly=True, copy=False, store=True, default='draft')

    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

    price_reduce = fields.Float(compute='_get_price_reduce', string='Price Reduce', digits='Product Price',
                                readonly=True, store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])
    price_reduce_taxinc = fields.Monetary(compute='_get_price_reduce_tax', string='Price Reduce Tax inc', readonly=True,
                                          store=True)
    price_reduce_taxexcl = fields.Monetary(compute='_get_price_reduce_notax', string='Price Reduce Tax excl',
                                           readonly=True, store=True)

    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    issue_lines = fields.One2many('sale.order.line', 'contract_line_id', string='Issue Lines', copy=False)
    qty_issued = fields.Float('Issued Quantity', copy=False, compute='_compute_qty_issued',
                              compute_sudo=True, store=True, digits='Product Unit of Measure', default=0.0)

    @api.depends('issue_lines.state', 'issue_lines.product_uom_qty')
    def _compute_qty_issued(self):
        for line in self:
            qty = 0.0
            for inv_line in line.issue_lines:
                if inv_line.state not in ['cancel']:
                    qty += inv_line.product_uom._compute_quantity(inv_line.product_uom_qty, line.product_uom)

            line.qty_issued = qty

    def name_get(self):
        result = []
        for so_line in self.sudo():
            name = '%s - %s' % (
                so_line.contract_id.name, so_line.name and so_line.name.split('\n')[0] or so_line.product_id.name)
            if so_line.partner_id.ref:
                name = '%s (%s)' % (name, so_line.partner_id.ref)
            result.append((so_line.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator in ('ilike', 'like', '=', '=like', '=ilike'):
            args = expression.AND([
                args or [],
                ['|', ('contract_id.name', operator, name), ('name', operator, name)]
            ])
        return super(SaleContractLine, self)._name_search(name, args=args, operator=operator, limit=limit,
                                                          name_get_uid=name_get_uid)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.contract_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.contract_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    def get_sale_order_line_multiline_description_sale(self, product):
        """ Compute a default multiline description for this sales order line.

        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
          the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        return product.get_product_multiline_description_sale()

    def _compute_tax_id(self):
        for line in self:
            fpos = line.contract_id.partner_id.property_account_position_id
            # If company_id is set in the order, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda r: r.company_id == line.contract_id.company_id)
            line.tax_id = fpos.map_tax(taxes, line.product_id, line.contract_id.partner_shipping_id) if fpos else taxes

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.contract_id.partner_id.lang).code,
            partner=self.contract_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.contract_id.date_contract,
            pricelist=self.contract_id.pricelist_id.id,
            uom=self.product_uom.id
        )
        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

        self._compute_tax_id()

        self.update(vals)

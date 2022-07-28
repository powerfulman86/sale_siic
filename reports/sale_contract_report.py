# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, fields, models


class SaleContractReport(models.Model):
    _name = "sale.contract.report"
    _description = "Sales Contract Analysis Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    name = fields.Char('Order Reference', readonly=True)
    date = fields.Datetime('Contract Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product Variant', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    product_uom_qty = fields.Float('Qty Ordered', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    price_total = fields.Float('Total', readonly=True)
    price_subtotal = fields.Float('Untaxed Total', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    nbr = fields.Integer('# of Lines', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('progress', 'In Progress'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', )
    weight = fields.Float('Gross Weight', readonly=True)
    volume = fields.Float('Volume', readonly=True)

    discount = fields.Float('Discount %', readonly=True)
    discount_amount = fields.Float('Discount Amount', readonly=True)
    campaign_id = fields.Many2one('utm.campaign', 'Campaign')
    contract_id = fields.Many2one('sale.contract', 'Contract #', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(l.id) as id,
            l.product_id as product_id,
            t.uom_id as product_uom,
            sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
            sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_total,
            sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_subtotal,
            count(*) as nbr,
            s.name as name,
            s.date_contract as date,
            s.state as state,
            s.partner_id as partner_id,
            s.user_id as user_id,
            t.categ_id as categ_id,
            s.pricelist_id as pricelist_id,
            s.team_id as team_id,
            p.product_tmpl_id,
            partner.country_id as country_id,
            partner.industry_id as industry_id,
            partner.commercial_partner_id as commercial_partner_id,
            sum(p.weight * l.product_uom_qty / u.factor * u2.factor) as weight,
            sum(p.volume * l.product_uom_qty / u.factor * u2.factor) as volume,
            l.discount as discount,
            sum((l.price_unit * l.product_uom_qty * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END)) as discount_amount,
            s.id as contract_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                sale_contract_line l
                      join sale_contract s on (l.contract_id=s.id)
                      join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=l.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)
                    left join product_pricelist pp on (s.pricelist_id = pp.id)
                %s
        """ % from_clause

        groupby_ = """
            l.product_id,
            l.contract_id,
            t.uom_id,
            t.categ_id,
            s.name,
            s.date_contract,
            s.partner_id,
            s.user_id,
            s.state,
            s.company_id,
            s.campaign_id,
            s.medium_id,
            s.source_id,
            s.pricelist_id,
            s.team_id,
            p.product_tmpl_id,
            partner.country_id,
            partner.industry_id,
            partner.commercial_partner_id,
            l.discount,
            s.id %s
        """ % (groupby)

        return '%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))


class SaleOrderReportProforma(models.AbstractModel):
    _name = 'report.sale.contract.report_saleproforma'
    _description = 'Proforma Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.contract'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'sale.contract',
            'docs': docs,
            'proforma': True
        }

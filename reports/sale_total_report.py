# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleTotalReport(models.Model):
    _name = "sale.total.report"
    _description = "Sales Analysis Total Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    @api.model
    def _get_done_states(self):
        return ['sale', 'done', 'paid']

    name = fields.Char('Order Reference', readonly=True)
    date = fields.Datetime('Order Date', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch", )
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    sale_contract = fields.Many2one('sale.contract', "Sale Contract", )
    order_source = fields.Selection(string="Order Source",
                                    selection=[('default', 'Default'), ('sugar', 'Sugar'), ('wood', 'Wood'), ], )
    # price_total = fields.Float('Total', readonly=True)
    # price_subtotal = fields.Float('Untaxed Total', readonly=True)
    # tax_amount = fields.Float('Tax Amount', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)
    order_id = fields.Many2one('sale.order', 'Order #', readonly=True)
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict')
    tax_value = fields.Float('Tax Value')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(s.id) as id,
            s.branch_id as branch_id,
            s.sale_contract as sale_contract,
            s.order_source as order_source,
            s.name as name,
            s.date_order as date,
            s.state as state,
            s.partner_id as partner_id,
            s.user_id as user_id,
            s.id as order_id,
            st.tax_id as tax_id,
            sum(st.amount) as tax_value
        """

        for field in fields.values():
            select_ += field

        from_ = """
                sale_order s 
                      join res_partner partner on s.partner_id = partner.id
                      left outer join sale_order_tax st on st.sale_id = s.id
                      left outer join account_tax at on st.tax_id = at.id 
                      join res_branch branch on s.branch_id = branch.id
                        left join sale_contract contract on s.sale_contract = contract.id
                      
                %s
        """ % from_clause

        groupby_ = """
            s.name,
            s.date_order,
            s.partner_id,
            s.user_id,
            s.state,
            st.tax_id,
            s.branch_id,
            s.sale_contract,
            s.order_source,
            s.id %s
        """ % (groupby)

        return '%s (SELECT %s FROM %s WHERE s.id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))


class SaleTotalReportProforma(models.AbstractModel):
    _name = 'report.sale.total.report_saleproforma'
    _description = 'Proforma Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'sale.order',
            'docs': docs,
            'proforma': True
        }

# -*- coding: utf-8 -*-

from odoo import fields, models


class DiscountSaleReport(models.Model):
    _inherit = 'sale.report'

    discount = fields.Float('Discount', readonly=True)
    order_type = fields.Selection(string="Type", selection=[('in', 'Local'), ('out', 'Foreign'), ], )
    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch", )
    delivery_company = fields.Many2one(comodel_name="res.partner", string="Delivery Company", )
    sale_contract = fields.Many2one('sale.contract', "Sale Contract", )
    order_source = fields.Selection(string="Order Source",
                                    selection=[('default', 'Default'), ('sugar', 'Sugar'), ('wood', 'Wood'), ], )
    shipping_type = fields.Selection(string="Shipping Type",
                                     selection=[('bycompany', 'By Company'), ('byclient', 'By Client'),
                                                ('noshipping', 'No Shipping'), ], )

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['order_type'] = ", s.order_type as order_type"
        fields['branch_id'] = ", s.branch_id as branch_id"
        fields['delivery_company'] = ", s.delivery_company as delivery_company"
        fields['sale_contract'] = ", s.sale_contract as sale_contract"
        fields['order_source'] = ", s.order_source as order_source"
        fields['shipping_type'] = ", s.shipping_type as shipping_type"
        groupby += ', s.order_type,s.branch_id,s.delivery_company,s.sale_contract,s.order_source,s.shipping_type'
        from_clause += """
                join res_branch branch on s.branch_id = branch.id
                left join res_partner delivery on s.delivery_company = delivery.id
                left join sale_contract contract on s.sale_contract = contract.id
        """

        return super(DiscountSaleReport, self)._query(with_clause, fields, groupby, from_clause)

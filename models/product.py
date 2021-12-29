# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    taxes_id = fields.Many2many('account.tax', 'category_taxes_rel', 'category_id', 'tax_id',
                                help="Default taxes used when selling the Category product.", string='Sales Taxes',
                                domain=[('type_tax_use', '=', 'sale')], )


class ProductProduct(models.Model):
    _inherit = 'product.template'

    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        if self.categ_id:
            taxes_ids = self.categ_id.taxes_id
            if len(taxes_ids) != 0:
                self.taxes_id = taxes_ids

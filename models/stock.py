from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_return_id = fields.Many2one(comodel_name='sale.return')


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_return_id = fields.Many2one(comodel_name='sale.return')

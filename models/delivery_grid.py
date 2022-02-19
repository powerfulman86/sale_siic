# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class ProviderGrid(models.Model):
    _inherit = 'delivery.carrier'

    def _get_price_from_picking(self, total, weight, volume, quantity):
        price = 0.0
        criteria_found = False
        price_dict = self._get_price_dict(total, weight, volume, quantity)
        if self.free_over and total >= self.amount:
            return 0
        for line in self.price_rule_ids:
            test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
            if test:
                price = (line.list_base_price + line.list_price) * price_dict[line.variable_factor]
                criteria_found = True
                break
        if not criteria_found:
            raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))

        return price

    def _get_price_available(self, order):
        self.ensure_one()
        self = self.sudo()
        order = order.sudo()
        total = weight = volume = quantity = 0
        total_delivery = 0.0
        for line in order.order_line:
            if line.state == 'cancel':
                continue
            if line.is_delivery:
                total_delivery += line.price_total
            if not line.product_id or line.is_delivery:
                continue

            qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            volume += (line.product_id.volume or 0.0) * qty
            quantity += qty
            weight += (line.weight_shipping or 0.0)
        total = (order.amount_total or 0.0) - total_delivery

        total = order.currency_id._convert(
            total, order.company_id.currency_id, order.company_id, order.date_order or fields.Date.today())

        return self._get_price_from_picking(total, weight, volume, quantity)
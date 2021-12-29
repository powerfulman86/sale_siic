# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vehicle_ids = fields.One2many(comodel_name="sale.delivery.vehicle", inverse_name="partner_id", string="Vehicles",
                                  required=False, )


class SaleDeliveryVehicle(models.Model):
    _name = 'sale.delivery.vehicle'
    _description = "Sale Delivery Vehicle"
    _rec_name = 'vehicle_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Integer(string='Sequence', default=10)
    partner_id = fields.Many2one(comodel_name="res.partner", string="Company", required=True,
                                 domain="[('company_id', '=', True),('delivery_company', '=', True)]")
    vehicle_number = fields.Integer(string="Number", required=True, index=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    engine_number = fields.Char('Engine Number', required=True, )
    note = fields.Text(string="Note", track_visibility='always')

    _sql_constraints = [
        (
            "vehicle_number_uniq",
            "unique(vehicle_number)",
            "Vehicle Id must be unique across the database!",
        )
    ]

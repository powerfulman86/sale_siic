# -*- coding: utf-8 -*-
# from odoo import http


# class SaleSiicCustom(http.Controller):
#     @http.route('/sale_siic_custom/sale_siic_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_siic_custom/sale_siic_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_siic_custom.listing', {
#             'root': '/sale_siic_custom/sale_siic_custom',
#             'objects': http.request.env['sale_siic_custom.sale_siic_custom'].search([]),
#         })

#     @http.route('/sale_siic_custom/sale_siic_custom/objects/<model("sale_siic_custom.sale_siic_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_siic_custom.object', {
#             'object': obj
#         })

# -*- coding: utf-8 -*-
{
    'name': "Sales SIIC Customization",
    'summary': """  Custom Application To Sales SIIC Customization """,
    'description': """ Sales SIIC Customization  """,
    'author': "SIIC",
    'category': 'Sales',
    'depends': ['base', 'portal', 'sale', 'account', 'multi_branch'],
    'data': [
        # 'security/security.xml',
        'security/ir.model.access.csv',
        'views/sale_view.xml',
        'views/account_invoice_view.xml',
        'views/invoice_report.xml',
        'views/sale_order_report.xml',
        'views/res_config_view.xml',
        'views/product_category.xml',
        'views/delivery_vehicle.xml',
        'views/sale_contract.xml',
        'views/sale_return.xml',
        'reports/sale_net_report.xml',
        'reports/sale_return_report.xml',
    ],
    'images': ['static/description/icon.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

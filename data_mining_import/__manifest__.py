{
    'name': "Data mining Dataset",
    'summary': """Sample Data for Data mining""",
    'author': "UIT Team",
    'category': 'data mining',
    'version': '1.0.0',
    'depends': ['sale','base','mail'],
    'data': [
        'data/customer_data.xml',
        'data/product_data.xml',
        'data/sale_order_data.xml',
        'data/order_line_data.xml',
    ],
        
    'application' :True, #defaults: False
    'auto_install': False,#defaults: False
}

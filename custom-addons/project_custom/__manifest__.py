# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Custom',
    'version': '0.1.0',
    'category': 'Academic',
    'sequence': 15,
    'summary': 'Custom Project Module',
    'author': 'Uchunzhyan Mikhail',
    # 'website': 'https://github.com/sefasenlik/PaLMS',
    'installable': True,
    'auto_install': True,
    'application': False,
    'depends' : ['project'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/project_task_view.xml'
    ],
    # 'license': 'LGPL-3'
}

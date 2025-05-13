{
    # Name of the module
    'name': 'Decidely',

    # Version of the module
    'version': '1.0.0',

    # Category under which the module will be listed in Odoo apps
    'category': 'Tools',

    # Short description of the module
    'summary': 'Voting table',

    # Author information and license note
    'author': 'Uchunzhyan Mikhail (CC BY-NC) 2025',

    # URL to the module's homepage or repository
    'website': 'https://github.com/muchunzyan/projects_monitoring',

    # License type for the module
    'license': 'LGPL-3',

    # Whether the module can be installed manually
    'installable': True,

    # Whether the module should be automatically installed as a dependency
    'auto_install': True,

    # Whether the module is a full-fledged application
    'application': True,

    # List of dependent modules required for this module to work
    'depends': [
        'mail',
    ],

    # List of data files (XML/CSV) to load during module installation
    'data': [
        'security/ir.model.access.csv',
        'data/export_template_poll.xml',
        'views/poll_poll_views.xml',
        'views/poll_menus.xml',
    ],
}

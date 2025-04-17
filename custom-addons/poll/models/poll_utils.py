from markupsafe import Markup
from odoo import api, fields, models


class StudentUtils(models.AbstractModel):
    _name = 'poll.utils'
    _description = 'Decidely - Utility Methods'

    @api.model
    def send_message(context, message_text, recipients, author, data_tuple=-1):
        tuple_id, tuple_name = data_tuple

        channel_name = "Poll №" + tuple_id + " (" + tuple_name + ")"

        channel = context.env['discuss.channel'].sudo().search([('name', '=', channel_name)], limit=1, )

        if not channel:
            channel = context.env['discuss.channel'].with_context(mail_create_nosubscribe=True).sudo().create({
                'channel_partner_ids': [(6, 0, [author.partner_id.id] + [r.partner_id.id for r in recipients])],
                'channel_type': 'channel',
                'name': channel_name,
                'display_name': channel_name
            })
        else:
            channel.write({
                'channel_partner_ids': [(6, 0, [author.partner_id.id] + [r.partner_id.id for r in recipients])]
            })

        channel.sudo().message_post(
            body=Markup(message_text),
            author_id=author.partner_id.id,
            message_type="comment",
            subtype_xmlid='mail.mt_comment'
        )

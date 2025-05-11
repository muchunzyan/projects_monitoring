from markupsafe import Markup
from odoo import api, fields, models


class PollUtils(models.AbstractModel):
    _name = 'poll.utils'
    _description = 'Decidely - Utility Methods'

    # @api.model
    # def send_message(context, message_text, recipients, author, data_tuple=-1):
    #     tuple_id, tuple_name = data_tuple
    #
    #     channel_name = "Poll №" + tuple_id + " (" + tuple_name + ")"
    #
    #     channel = context.env['discuss.channel'].sudo().search([('name', '=', channel_name)], limit=1, )
    #
    #     if not channel:
    #         channel = context.env['discuss.channel'].with_context(mail_create_nosubscribe=True).sudo().create({
    #             'channel_partner_ids': [(6, 0, [author.partner_id.id] + [r.partner_id.id for r in recipients])],
    #             'channel_type': 'channel',
    #             'name': channel_name,
    #             'display_name': channel_name
    #         })
    #
    #         channel.write({
    #             'channel_partner_ids': [(4, recipient.partner_id.id) for recipient in recipients]
    #         })
    #
    #     channel.sudo().message_post(
    #         body=Markup(message_text),
    #         author_id=author.partner_id.id,
    #         message_type="comment",
    #         subtype_xmlid='mail.mt_comment'
    #     )

    @api.model
    def send_message(context, source, message_text, recipients, author, data_tuple=-1):
        tuple_id, tuple_name = data_tuple

        if source == 'poll':
            channel_name = "Poll №" + tuple_id + " (" + tuple_name + ")"
        else:
            raise ValueError(f"Unknown source type: {source}")

        # Search the channel to avoid duplicates
        channel = context.env['discuss.channel'].sudo().search([('name', '=', channel_name)], limit=1, )

        # If no suitable channel is found, create a new channel
        if not channel:
            channel = context.env['discuss.channel'].with_context(mail_create_nosubscribe=True).sudo().create({
                'channel_partner_ids': [(6, 0, author.partner_id.id)],
                'channel_type': 'channel',
                'name': channel_name,
                'display_name': channel_name
            })

            channel.write({
                'channel_partner_ids': [(4, recipient.partner_id.id) for recipient in recipients]
            })

        # Send a message to the related user
        channel.sudo().message_post(
            body=Markup(message_text),
            author_id=author.partner_id.id,
            message_type="comment",
            subtype_xmlid='mail.mt_comment'
        )

    # Displays notification messages
    def message_display(self, title, message, sticky_bool):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _(title),
                'message': message,
                'sticky': sticky_bool,
                'next': {
                    'type': 'ir.actions.act_window_close',
                }
            }
        }

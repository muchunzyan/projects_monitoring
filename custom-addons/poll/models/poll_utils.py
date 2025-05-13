from markupsafe import Markup
from odoo import api, fields, models


# Utility model providing helper functions for the Poll module
class PollUtils(models.AbstractModel):
    _name = 'poll.utils'
    _description = 'Decidely - Utility Methods'

    # Sends a message to a Discuss channel, creating it if necessary
    @api.model
    def send_message(context, source, message_text, recipients, author, data_tuple=-1):
        # Extract ID and name from data_tuple to construct the channel name
        tuple_id, tuple_name = data_tuple

        # Determine the message context (currently only 'poll' is supported)
        if source == 'poll':
            channel_name = "Poll №" + tuple_id + " (" + tuple_name + ")"
        else:
            raise ValueError(f"Unknown source type: {source}")

        # Look for an existing Discuss channel with this name
        channel = context.env['discuss.channel'].sudo().search([('name', '=', channel_name)], limit=1)

        # If no such channel exists, create a new one
        if not channel:
            channel = context.env['discuss.channel'].with_context(mail_create_nosubscribe=True).sudo().create({
                'channel_partner_ids': [(6, 0, author.partner_id.id)],  # Set initial author
                'channel_type': 'channel',
                'name': channel_name,
                'display_name': channel_name
            })

            # Add recipients to the channel
            channel.write({
                'channel_partner_ids': [(4, recipient.partner_id.id) for recipient in recipients]
            })

        # Post the message in the channel
        channel.sudo().message_post(
            body=Markup(message_text),  # Use Markup to safely render HTML
            author_id=author.partner_id.id,
            message_type="comment",
            subtype_xmlid='mail.mt_comment'
        )

    # Displays a browser notification message to the user
    def message_display(self, title, message, sticky_bool):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _(title),           # Title of the notification
                'message': message,          # Message content
                'sticky': sticky_bool,       # Whether the notification stays until dismissed
                'next': {
                    'type': 'ir.actions.act_window_close',  # Close the action window after display
                }
            }
        }

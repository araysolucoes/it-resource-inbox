# -*- coding: utf-8 -*-
"""Compose wizard used to write new emails and replies.

The wizard collects recipient, subject and body (plain text, or HTML loaded
from an uploaded file), shows a live preview with the account banner and then
delegates the actual sending to ``email.account._send``.
"""
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_LAYOUT_EXT = ('html', 'htm', 'xml', 'hml')


class EmailCompose(models.TransientModel):
    _name = 'email.compose'
    _description = 'Compose Email'

    account_id = fields.Many2one(
        'email.account',
        string='Send From Account',
        required=True,
        domain=[('active', '=', True), ('smtp_enabled', '=', True)],
        help='The message goes out through this account\'s SMTP. The account must have sending enabled.',
    )
    parent_id = fields.Many2one(
        'email.message',
        string='Original Message',
        help='Message this reply continues.',
    )
    template_id = fields.Many2one(
        'email.template',
        string='Template',
        domain=[('active', '=', True)],
        help='Fills in subject and body. {{{variable}}} and {{key}} are replaced when there is an origin record.',
    )
    email_to = fields.Char(
        string='To',
        required=True,
        help='Address of the recipient. Can be more than one, separated by commas.',
    )
    email_cc = fields.Char(
        string='Cc',
        help='Who also receives it, as a visible copy. Separate multiple addresses with commas.',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'email_compose_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Attachments',
        help='Files sent along with the message.',
    )
    subject = fields.Char(
        string='Subject',
        help='Line shown in the recipient\'s inbox.',
    )
    body_format = fields.Selection(
        [('text', 'Text'), ('html', 'HTML')],
        string='Content Type',
        default='text',
        required=True,
        help='Text is a plain letter. HTML uses the .html, .htm, .xml or .hml file.',
    )
    body = fields.Text(
        string='Message',
        help='Text of the letter, or the HTML read from the file.',
    )
    layout_file = fields.Binary(string='HTML File')
    layout_filename = fields.Char(string='File Name')
    preview_html = fields.Html(
        string='Preview',
        compute='_compute_preview_html',
        sanitize=False,
    )
    res_model = fields.Char(string='Origin Module')
    res_id = fields.Integer(string='Origin Record ID')
    mode = fields.Selection(
        [('new', 'New Message'), ('reply', 'Reply')],
        default='new',
        required=True,
    )

    @api.depends('body', 'body_format', 'account_id', 'account_id.signature_image', 'account_id.signature_filename')
    def _compute_preview_html(self):
        for wizard in self:
            wizard.preview_html = wizard.account_id._message_preview_html(
                wizard.body, wizard.body_format,
            )

    @api.model
    def default_get(self, fields_list):
        """Preselect the sending account when the choice is obvious."""
        values = super(EmailCompose, self).default_get(fields_list)
        # If only one account can send, it is preselected. Otherwise the
        # default account is used, when it has sending enabled.
        if 'account_id' in fields_list and not values.get('account_id'):
            accounts = self.env['email.account'].search([
                ('active', '=', True),
                ('smtp_enabled', '=', True),
            ], limit=2)
            if len(accounts) == 1:
                values['account_id'] = accounts.id
            else:
                default = self.env['email.account'].search([
                    ('active', '=', True),
                    ('smtp_enabled', '=', True),
                    ('is_default', '=', True),
                ], limit=1)
                if default:
                    values['account_id'] = default.id
        return values

    @api.onchange('template_id')
    def _onchange_template_id(self):
        template = self.template_id
        if not template:
            return
        record = self.env[self.res_model].browse(self.res_id).exists() if self.res_model and self.res_id else template.browse()
        if template.account_id:
            self.account_id = template.account_id
        self.body_format = template.body_format
        self.subject = template._render_text(template.subject, record, {})
        self.body = template._render_text(template.body, record, {})
        if self.mode == 'new':
            rendered_to = template._render_text(template.email_to, record, {})
            if rendered_to:
                self.email_to = rendered_to

    @api.onchange('layout_file', 'layout_filename')
    def _onchange_layout_file(self):
        if not self.layout_file or not self.layout_filename:
            return
        ext = self.layout_filename.rsplit('.', 1)[-1].lower()
        if ext not in _LAYOUT_EXT:
            self.layout_file = False
            self.layout_filename = False
            return {
                'warning': {
                    'title': _('File not accepted'),
                    'message': _('Use a .html, .htm, .xml or .hml file.'),
                },
            }
        raw = base64.b64decode(self.layout_file)
        self.body = raw.decode('utf-8', errors='replace')
        self.body_format = 'html'

    def action_send(self):
        """Send the message and open it in the Sent list."""
        return self._open_message(self._compose(deliver=True))

    def _compose(self, deliver):
        self.ensure_one()
        if self.body_format == 'html' and not (self.body or '').strip():
            raise UserError(_('Upload a .html, .htm, .xml or .hml file, or write the HTML.'))
        parent = self.parent_id
        in_reply_to = False
        if self.mode == 'reply' and parent:
            in_reply_to = parent.message_id
        return self.account_id.sudo()._send(
            email_to=self.email_to,
            subject=self.subject,
            body=self.body,
            body_format=self.body_format,
            parent=parent if self.mode != 'new' else None,
            res_model=self.res_model,
            res_id=self.res_id,
            in_reply_to=in_reply_to,
            email_cc=self.email_cc,
            attachment_ids=self.attachment_ids.ids,
            deliver=deliver,
            template=self.template_id,
        )

    def _open_message(self, message):
        # Open the record through the Sent action so the breadcrumb and menu
        # context belong to Sent, instead of inheriting the Inbox menu the user
        # may have come from.
        action = self.env.ref('email_inbox.action_email_message_sent').sudo().read()[0]
        action.update({
            'res_id': message.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        })
        return action

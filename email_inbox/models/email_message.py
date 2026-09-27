# -*- coding: utf-8 -*-
"""Stored email messages, both sent (SMTP) and received (POP3).

Each ``email.message`` belongs to one ``email.account``. Replies are linked to
the message they answer through ``parent_id`` and inherit ``res_model`` /
``res_id``, so other modules can read the whole conversation of a record with
``thread_for``. Computed fields split the body into the new answer and the
quoted history to make messages easier to read.
"""
import html
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmailMessage(models.Model):
    _name = 'email.message'
    _description = 'Email Message'
    _order = 'date desc, id desc'
    _rec_name = 'subject'

    account_id = fields.Many2one(
        'email.account',
        string='Account Used',
        required=True,
        ondelete='restrict',
        index=True,
        help='System account that sent or downloaded this message.',
    )
    direction = fields.Selection(
        [('in', 'Received'), ('out', 'Sent')],
        string='Direction',
        required=True,
        index=True,
        help='Received came in through POP3. Sent went out through this account\'s SMTP.',
    )
    in_inbox = fields.Boolean(
        string='In Inbox',
        default=True,
        index=True,
        help='Reply to an email we sent. Everything else goes to Others.',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('received', 'Received'),
            ('error', 'Failed'),
        ],
        string='Status',
        required=True,
        default='draft',
        help='Failed means the SMTP server refused the message. The reason is shown in the red banner.',
    )
    message_id = fields.Char(
        string='Message Identifier',
        index=True,
        copy=False,
        help='Unique code used to link a reply to the original message.',
    )
    in_reply_to = fields.Char(
        string='In Reply To',
        copy=False,
        help='Identifier of the previous message in this conversation.',
    )
    subject = fields.Char(string='Subject')
    body = fields.Text(string='Body')
    body_format = fields.Selection(
        [('text', 'Text'), ('html', 'HTML')],
        string='Format',
        default='text',
        required=True,
        help='Text is a plain letter. HTML is the page sent from the uploaded file.',
    )
    preview = fields.Char(string='Preview', compute='_compute_reading')
    reply_text = fields.Text(string='Reply', compute='_compute_reading')
    quote_text = fields.Text(string='Quote', compute='_compute_reading')
    reading_html = fields.Html(string='Reading View', compute='_compute_reading', sanitize=False)
    email_from = fields.Char(
        string='Sender',
        help='Who sent it. On a received message, this is the outside person.',
    )
    email_to = fields.Char(
        string='Recipient',
        help='Who should receive it. On a sent message, this is the outside person. Separate multiple addresses with commas.',
    )
    email_cc = fields.Char(
        string='Cc',
        help='Addresses that receive a visible copy. Separate multiple addresses with commas.',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'email_message_attachment_rel',
        'message_id',
        'attachment_id',
        string='Attachments',
        help='Files sent along with the message.',
    )
    template_id = fields.Many2one(
        'email.template',
        string='Template Used',
        readonly=True,
        help='Template that generated this message, when sending was triggered by another module.',
    )
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    parent_id = fields.Many2one(
        'email.message',
        string='Previous Message',
        ondelete='set null',
        index=True,
        help='Message this one replies to or forwards.',
    )
    child_ids = fields.One2many('email.message', 'parent_id', string='Follow-ups')
    # Generic link (model name + record id) to the record of another module that
    # started or follows this thread. A plain Char/Integer pair is used instead of
    # a Reference field so any module can use it without being a dependency.
    res_model = fields.Char(
        string='Origin Module',
        index=True,
        help='Filled in automatically when another module sends through this inbox.',
    )
    res_id = fields.Integer(
        string='Origin Record ID',
        index=True,
        help='ID of the record that requested the sending, in the origin module.',
    )
    error_message = fields.Text(
        string='Failure Reason',
        readonly=True,
        help='Text returned by the outgoing server when the message could not be sent.',
    )

    @api.onchange('account_id')
    def _onchange_account_id(self):
        # For outgoing mail the sender is always the account address, so the
        # form does not ask for it; it is copied here whenever the account changes.
        if self.direction != 'in' and self.account_id:
            self.email_from = self.account_id.email

    @api.model_create_multi
    def create(self, vals_list):
        """Default the sender of outgoing messages to the account address."""
        accounts = self.env['email.account']
        for vals in vals_list:
            if vals.get('direction') == 'in' or vals.get('email_from') or not vals.get('account_id'):
                continue
            vals['email_from'] = accounts.browse(vals['account_id']).email
        return super(EmailMessage, self).create(vals_list)

    def write(self, vals):
        """Keep the sender of outgoing messages in sync when the account changes."""
        if vals.get('account_id') and 'email_from' not in vals:
            account = self.env['email.account'].browse(vals['account_id'])
            outgoing = self.filtered(lambda message: (vals.get('direction') or message.direction) != 'in')
            if outgoing and account.email and outgoing == self:
                vals = dict(vals, email_from=account.email)
        return super(EmailMessage, self).write(vals)

    @api.depends('body', 'body_format', 'account_id.signature_image', 'account_id.signature_filename')
    def _compute_reading(self):
        for message in self:
            if message.body_format == 'html':
                answer, quote = message.body or '', ''
            else:
                answer, quote = self._split_body(message.body)
            message.reply_text = answer
            message.quote_text = quote
            message.preview = self._plain_preview(answer)
            message.reading_html = message.account_id._message_preview_html(
                message.body, message.body_format or 'text',
            )

    def init(self):
        """Move already-downloaded non-replies out of the inbox.

        When the "Replies Only" option was introduced, previously fetched mail
        was all flagged as inbox. This recomputes ``in_inbox`` so that only
        messages answering one of our sent emails stay in the inbox for
        accounts with ``only_replies`` on. The column check skips the update
        on the very first install, before ``email_account`` has that column.
        """
        self.env.cr.execute("""
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'email_account'
               AND column_name = 'only_replies'
        """)
        if not self.env.cr.fetchone():
            return
        self.env.cr.execute("""
            UPDATE email_message AS incoming
               SET in_inbox = EXISTS (
                    SELECT 1
                      FROM email_message AS parent
                     WHERE parent.id = incoming.parent_id
                       AND parent.direction = 'out'
               )
              FROM email_account AS account
             WHERE incoming.account_id = account.id
               AND incoming.direction = 'in'
               AND account.only_replies = TRUE
        """)

    @api.model
    def _plain_preview(self, text):
        # Strip scripts, styles, comments, tags and HTML entities so the
        # kanban preview is plain readable text, capped at 160 characters.
        raw = text or ''
        raw = re.sub(r'(?is)<(script|style)\b[^>]*>.*?</\1>', ' ', raw)
        raw = re.sub(r'(?is)<!--.*?-->', ' ', raw)
        raw = re.sub(r'(?i)<br\s*/?>', ' ', raw)
        raw = re.sub(r'(?i)</(p|div|tr|li|h[1-6]|table)>', ' ', raw)
        raw = re.sub(r'<[^>]+>', ' ', raw)
        raw = html.unescape(raw).replace('\xa0', ' ')
        raw = re.sub(r'\s+', ' ', raw).strip()
        return raw[:160]

    @api.model
    def _split_body(self, body):
        # Separate what the person just wrote from the quoted previous message.
        # Mail clients introduce the quote with a header line whose wording
        # depends on the client language, so both English and Portuguese
        # markers are recognised:
        #   - "On <date>, <sender> wrote:"       (English Gmail/Apple Mail)
        #   - "Em <date>, <sender> escreveu:"    (Portuguese Gmail)
        #   - "--- Mensagem original ---"        (Portuguese Outlook)
        #   - "De: ... / Enviado em: ..."        (Portuguese Outlook headers)
        # The earliest marker found wins. When no marker exists, the first
        # block of lines starting with ">" is treated as the quote. If cutting
        # would leave an empty answer, the whole text is kept as the answer.
        text = (body or '').replace('\r\n', '\n').replace('\r', '\n').strip()
        if not text:
            return '', ''
        markers = (
            r'\nEm [^\n]+ escreveu:\s*\n',
            r'\nOn [^\n]+ wrote:\s*\n',
            r'\n-{3,} ?Mensagem original ?-{3,}',
            r'\nDe: [^\n]+\nEnviado em: ',
        )
        cut = None
        padded = '\n' + text
        for pattern in markers:
            match = re.search(pattern, padded, re.I)
            if not match:
                continue
            index = max(match.start() - 1, 0)
            if cut is None or index < cut:
                cut = index
        if cut is None:
            lines = text.split('\n')
            for index, line in enumerate(lines):
                if not line.startswith('>'):
                    continue
                while index > 0 and not lines[index - 1].strip():
                    index -= 1
                answer = '\n'.join(lines[:index]).strip()
                quote = '\n'.join(lines[index:]).strip()
                if answer:
                    return answer, quote
                return text, ''
            return text, ''
        answer = text[:cut].strip()
        quote = text[cut:].strip()
        if not answer:
            return text, ''
        return answer, quote

    @api.model
    def thread_for(self, res_model, res_id):
        """Return the conversation linked to another module's record, newest first."""
        return self.search([
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
        ])

    def action_open_origin(self):
        """Open the record of another module this message is linked to."""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_('This message is not linked to a record of another module.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Origin Record'),
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_draft(self):
        """Send an outgoing draft through the account's SMTP."""
        self.ensure_one()
        if self.direction != 'out' or self.state != 'draft':
            raise UserError(_('Only an outgoing draft can be sent from here.'))
        return self._deliver_outgoing()

    def _deliver_outgoing(self):
        # Deliver a draft or a failed message through the account's SMTP without
        # opening the account form. The state and the failure reason are stored
        # before raising so the user sees why the message did not go out.
        self.ensure_one()
        try:
            self.account_id.sudo()._smtp_deliver(self)
        except Exception as exc:
            self.write({'state': 'error', 'error_message': str(exc)})
            raise UserError(_('Sending failed: %s') % exc)
        self.write({'state': 'sent', 'error_message': False})
        return True

    def action_retry(self):
        """Try again to send an outgoing message that failed."""
        self.ensure_one()
        if self.direction != 'out' or self.state != 'error':
            raise UserError(_('Only an outgoing message that failed can be resent.'))
        return self._deliver_outgoing()

    def action_reply(self):
        """Open the compose wizard prefilled as a reply to this message."""
        self.ensure_one()
        subject = self.subject or ''
        if not subject.lower().startswith('re:'):
            subject = 'Re: %s' % subject
        reply_to = self.email_from if self.direction == 'in' else self.email_to
        return self._open_compose('reply', reply_to, subject)

    def _open_compose(self, mode, email_to, subject):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reply'),
            'res_model': 'email.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_id': self.account_id.id,
                'default_parent_id': self.id,
                'default_email_to': email_to or '',
                'default_subject': subject,
                'default_body': (self.reply_text or self.body or '') if self.body_format != 'html' else '',
                'default_body_format': 'text',
                'default_res_model': self.res_model,
                'default_res_id': self.res_id,
                'default_mode': mode,
            },
        }

# -*- coding: utf-8 -*-
"""Email accounts: SMTP sending, POP3 fetching and reply threading.

An ``email.account`` holds the credentials of one mailbox. Picking a provider
fills in host, port and encryption, so users only type the address and the
password. Each account is mirrored into Odoo's native ``ir.mail_server`` and
``fetchmail.server`` lists, and exposes a small API (``send_for_record``,
``get_default_account``, ``get_by_code``) that other modules use to send mail
tied to their own records and to receive the replies back on those records.
"""
import base64
import logging
import re
import smtplib
import poplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from email.utils import parsedate_to_datetime
from html import escape
from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)

# Server, port and encryption for each supported provider. The form never asks
# for these values: choosing the provider is enough, and these presets are
# written on create/write/onchange so the account is ready to connect.
PROVIDER_PRESETS = {
    'gmail': {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_tls': True,
        'smtp_ssl': False,
        'pop3_host': 'pop.gmail.com',
        'pop3_port': 995,
        'pop3_ssl': True,
    },
    'outlook': {
        'smtp_host': 'smtp.office365.com',
        'smtp_port': 587,
        'smtp_tls': True,
        'smtp_ssl': False,
        'pop3_host': 'outlook.office365.com',
        'pop3_port': 995,
        'pop3_ssl': True,
    },
    'hostinger': {
        'smtp_host': 'smtp.hostinger.com',
        'smtp_port': 465,
        'smtp_tls': False,
        'smtp_ssl': True,
        'pop3_host': 'pop.hostinger.com',
        'pop3_port': 995,
        'pop3_ssl': True,
    },
    'localweb': {
        'smtp_host': 'smtp.localweb.com.br',
        'smtp_port': 587,
        'smtp_tls': True,
        'smtp_ssl': False,
        'pop3_host': 'pop.localweb.com.br',
        'pop3_port': 995,
        'pop3_ssl': True,
    },
}
_BANNER_EXT = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
}


class _SmtpMudo(object):
    """No-op SMTP client used while tests run.

    Module updates executed with ``--test-enable`` run against the real
    database and real accounts; this stub is returned instead of a live
    connection so no real email ever leaves the server during tests.
    """

    def send_message(self, mime):
        return None

    def login(self, user, password):
        return None

    def quit(self):
        return None


class EmailAccount(models.Model):
    _name = 'email.account'
    _description = 'Email Account'
    _order = 'name'

    name = fields.Char(
        string='Internal Name',
        required=True,
        help='Name used only to find the account in the list. Example: Support or Billing.',
    )
    email = fields.Char(
        string='Email',
        required=True,
        help='Address that sends and receives. The provider login uses this same address.',
    )
    provider = fields.Selection(
        [
            ('gmail', 'Gmail'),
            ('outlook', 'Outlook'),
            ('hostinger', 'Hostinger'),
            ('localweb', 'Localweb'),
        ],
        string='Provider',
        help='The system fills in server, port and encryption from this choice.',
    )
    smtp_enabled = fields.Boolean(
        string='Enable SMTP',
        help='When on, this account can send. When off, sending is blocked.',
    )
    pop_enabled = fields.Boolean(
        string='Enable POP',
        help='When on, the system downloads this account\'s mailbox. When off, fetching skips the account.',
    )
    only_replies = fields.Boolean(
        string='Replies Only',
        default=True,
        help='When on, the inbox only shows messages that reply to an email sent by the system.',
    )
    keep_others = fields.Boolean(
        string='Keep the Rest',
        default=True,
        help='When on, messages that are not replies go to the Others list. When off, that mail is ignored.',
    )
    active = fields.Boolean(
        string='Account in Use',
        default=True,
        help='When unchecked, the account stops sending and fetching messages.',
    )
    code = fields.Char(
        string='Code for Other Modules',
        copy=False,
        help='Stable name without spaces. Other modules look up the account by this code. Example: support.',
    )
    is_default = fields.Boolean(
        string='Default Account',
        help='Used when another module sends without choosing an account. Only one can be checked.',
    )
    signature_image = fields.Binary(
        string='Signature Banner',
        attachment=False,
        help='png, jpg or webp image added at the end of every message sent.',
    )
    signature_filename = fields.Char(string='Banner File Name')
    last_fetch = fields.Datetime(
        string='Last Fetch',
        readonly=True,
        help='Time of the last attempt to download the POP3 mailbox.',
    )
    last_fetch_error = fields.Text(
        string='Last Fetch Error',
        readonly=True,
        help='Filled in when POP3 refuses the connection or the login.',
    )
    smtp_host = fields.Char(
        string='Outgoing Server (SMTP)',
        help='Server that sends. Gmail: smtp.gmail.com. Outlook: smtp.office365.com.',
    )
    smtp_port = fields.Integer(
        string='Outgoing Port',
        default=587,
        help='Use 587 with STARTTLS, which is the default on this form.',
    )
    smtp_user = fields.Char(
        string='Outgoing Username',
        help='Usually the account address itself.',
    )
    smtp_password = fields.Char(
        string='Outgoing Password',
        groups='email_inbox.group_email_manager',
        help='Account password, or app password if the provider requires one.',
    )
    smtp_tls = fields.Boolean(
        string='Encrypt Sending (STARTTLS)',
        default=True,
        help='Port 587. The connection starts in plain text and is then upgraded to encrypted.',
    )
    smtp_ssl = fields.Boolean(
        string='Direct SSL for Sending',
        help='Port 465, as used by Hostinger. The connection is encrypted from the start.',
    )
    pop3_host = fields.Char(
        string='Incoming Server (POP3)',
        help='Server the system downloads incoming mail from. Gmail: pop.gmail.com. '
             'Outlook: outlook.office365.com.',
    )
    pop3_port = fields.Integer(
        string='Incoming Port',
        default=995,
        help='Use 995 with SSL. Port 110 is not encrypted.',
    )
    pop3_user = fields.Char(
        string='Incoming Mailbox Username',
        help='Username of the mailbox that receives the forwarded mail. Usually the account address.',
    )
    pop3_password = fields.Char(
        string='Incoming Mailbox Password',
        groups='email_inbox.group_email_manager',
        help='Password of the same mailbox configured for POP3.',
    )
    pop3_ssl = fields.Boolean(
        string='Encrypt Incoming (SSL)',
        default=True,
        help='Keep checked on port 995.',
    )
    mail_server_id = fields.Many2one(
        'ir.mail_server',
        string='Odoo Outgoing Server',
        copy=False,
        readonly=True,
        help='The same SMTP as this account, in the Outgoing Mail Servers list.',
    )
    fetchmail_server_id = fields.Many2one(
        'fetchmail.server',
        string='Odoo Incoming Server',
        copy=False,
        readonly=True,
        help='The same POP3 settings, in the Incoming Mail Servers list. It stays unconfirmed so that Email Inbox keeps downloading the messages.',
    )
    message_ids = fields.One2many('email.message', 'account_id', string='History')
    message_count = fields.Integer(
        string='Messages',
        compute='_compute_message_count',
    )
    error_count = fields.Integer(
        string='Send Failures',
        compute='_compute_message_count',
    )
    uidl_ids = fields.One2many('email.uidl', 'account_id', string='Downloaded UIDLs')

    _sql_constraints = [
        (
            'email_account_code_unique',
            'unique(code)',
            'An account with this code already exists.',
        ),
    ]

    def _compute_message_count(self):
        grouped = self.env['email.message'].read_group(
            [('account_id', 'in', self.ids)],
            ['account_id'],
            ['account_id'],
        )
        counts = {
            row['account_id'][0]: row['account_id_count']
            for row in grouped
            if row['account_id']
        }
        for account in self:
            account.message_count = counts.get(account.id, 0)
        failed = self.env['email.message'].read_group(
            [('account_id', 'in', self.ids), ('state', '=', 'error')],
            ['account_id'],
            ['account_id'],
        )
        failed_counts = {
            row['account_id'][0]: row['account_id_count']
            for row in failed
            if row['account_id']
        }
        for account in self:
            account.error_count = failed_counts.get(account.id, 0)

    def init(self):
        """Migrate accounts created before the provider field existed.

        Older records only had raw SMTP/POP3 hosts. The provider is guessed
        from those hosts and SMTP/POP are switched on when a host was set, so
        the accounts keep sending and receiving exactly as they did before.
        The POP3 password is also back-filled from the SMTP one because the
        form now uses a single password for both directions.
        """
        self.env.cr.execute("""
            UPDATE email_account
               SET provider = CASE
                     WHEN COALESCE(smtp_host, '') ILIKE '%%gmail%%'
                       OR COALESCE(pop3_host, '') ILIKE '%%gmail%%' THEN 'gmail'
                     WHEN COALESCE(smtp_host, '') ILIKE '%%office365%%'
                       OR COALESCE(smtp_host, '') ILIKE '%%outlook%%' THEN 'outlook'
                     WHEN COALESCE(smtp_host, '') ILIKE '%%hostinger%%' THEN 'hostinger'
                     WHEN COALESCE(smtp_host, '') ILIKE '%%localweb%%' THEN 'localweb'
                     ELSE 'gmail'
                   END,
                   smtp_enabled = CASE
                     WHEN COALESCE(smtp_host, '') <> '' THEN TRUE
                     ELSE FALSE
                   END,
                   pop_enabled = CASE
                     WHEN COALESCE(pop3_host, '') <> '' THEN TRUE
                     ELSE FALSE
                   END
             WHERE provider IS NULL
        """)
        self.env.cr.execute("""
            UPDATE email_account
               SET pop3_password = smtp_password
             WHERE COALESCE(pop3_password, '') = ''
               AND COALESCE(smtp_password, '') <> ''
        """)

    def write(self, vals):
        """Apply provider presets, keep one default account and resync Odoo servers."""
        touched = {'provider', 'email', 'smtp_password', 'signature_filename'}
        if touched.intersection(vals):
            for account in self:
                super(EmailAccount, account).write(self._prepare_account_vals(vals, account))
            result = True
        else:
            result = super(EmailAccount, self).write(vals)
        if vals.get('is_default') and not self.env.context.get('skip_default_account'):
            self._clear_other_defaults()
        if not self.env.context.get('skip_mail_server_sync'):
            self._sync_odoo_mail_servers()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Apply provider presets, keep one default account and create Odoo servers."""
        prepared = [self._prepare_account_vals(vals) for vals in vals_list]
        accounts = super(EmailAccount, self).create(prepared)
        accounts.filtered('is_default')._clear_other_defaults()
        accounts._sync_odoo_mail_servers()
        return accounts

    @api.model
    def _prepare_account_vals(self, vals, current=None):
        # The provider decides server and port, and the account address doubles
        # as SMTP and POP3 login. The form shows a single password field, so it
        # is copied to the POP3 password to be valid for sending and receiving.
        vals = dict(vals)
        if vals.get('provider') in PROVIDER_PRESETS:
            vals.update(PROVIDER_PRESETS[vals['provider']])
        if 'email' in vals or 'provider' in vals:
            email = vals.get('email') or (current.email if current else False)
            if email:
                vals['smtp_user'] = email
                vals['pop3_user'] = email
        if vals.get('email') and not vals.get('name') and not (current and current.name):
            vals['name'] = vals['email']
        if 'smtp_password' in vals:
            vals['pop3_password'] = vals['smtp_password']
        filename = vals.get('signature_filename')
        if filename:
            self._check_banner_name(filename)
        return vals

    @api.model
    def _check_banner_name(self, filename):
        ext = (filename or '').rsplit('.', 1)[-1].lower()
        if ext not in _BANNER_EXT:
            raise UserError(_('The banner must be a png, jpg or webp file.'))

    @api.onchange('provider', 'email')
    def _onchange_provider(self):
        if self.provider in PROVIDER_PRESETS:
            self.update(PROVIDER_PRESETS[self.provider])
        if self.email:
            self.smtp_user = self.email
            self.pop3_user = self.email
            if not self.name:
                self.name = self.email

    @api.onchange('smtp_password')
    def _onchange_smtp_password(self):
        self.pop3_password = self.smtp_password

    def _clear_other_defaults(self):
        # Other modules call get_default_account() without choosing an account,
        # so there must be exactly one default. Unchecking the others uses a
        # context flag to avoid re-entering this method from write().
        for account in self.filtered('is_default'):
            others = self.search([
                ('id', '!=', account.id),
                ('is_default', '=', True),
            ])
            if others:
                others.with_context(skip_default_account=True).write({'is_default': False})

    @api.model
    def _sync_existing_accounts(self):
        # Called from data XML on module install/update so that accounts saved
        # before the synchronisation existed also appear in Odoo's server lists.
        self.search([])._sync_odoo_mail_servers()

    def _sync_odoo_mail_servers(self):
        # Mirror SMTP and POP3 into Odoo's native server lists so standard
        # features (chatter, fetchmail screens) see the same configuration.
        # The incoming server is kept in draft on purpose: a confirmed server
        # would make the fetchmail cron download the same mailbox this module
        # already downloads, creating duplicates.
        for account in self:
            account._sync_one_outgoing()
            account._sync_one_incoming()

    def _sync_one_outgoing(self):
        self.ensure_one()
        account = self.sudo()
        ready = account.active and account.smtp_enabled and account.smtp_host
        if account.mail_server_id and not ready:
            account.mail_server_id.sudo().write({'active': False})
            return
        if not ready:
            return
        if account.smtp_ssl:
            encryption = 'ssl'
        elif account.smtp_tls:
            encryption = 'starttls'
        else:
            encryption = 'none'
        vals = {
            'name': account.name or account.email,
            'smtp_host': account.smtp_host,
            'smtp_port': account.smtp_port or (465 if account.smtp_ssl else 587),
            'smtp_encryption': encryption,
            'smtp_user': account.smtp_user or account.email,
            'smtp_pass': account.smtp_password or False,
            'active': True,
            'sequence': 1 if account.is_default else 10,
        }
        if account.mail_server_id:
            account.mail_server_id.sudo().write(vals)
        else:
            server = self.env['ir.mail_server'].sudo().create(vals)
            account.with_context(skip_mail_server_sync=True).write({
                'mail_server_id': server.id,
            })

    def _sync_one_incoming(self):
        self.ensure_one()
        account = self.sudo()
        ready = account.active and account.pop_enabled and account.pop3_host
        if account.fetchmail_server_id and not ready:
            account.fetchmail_server_id.sudo().write({'active': False, 'state': 'draft'})
            return
        if not ready:
            return
        vals = {
            'name': account.name or account.email,
            'server': account.pop3_host,
            'port': account.pop3_port or (995 if account.pop3_ssl else 110),
            'server_type': 'pop',
            'is_ssl': bool(account.pop3_ssl),
            'user': account.email or account.pop3_user,
            'password': account.pop3_password or account.smtp_password or False,
            'active': True,
            'state': 'draft',
        }
        if account.fetchmail_server_id:
            account.fetchmail_server_id.sudo().write(vals)
        else:
            server = self.env['fetchmail.server'].sudo().create(vals)
            account.with_context(skip_mail_server_sync=True).write({
                'fetchmail_server_id': server.id,
            })

    def unlink(self):
        """Delete accounts and archive their mirrored Odoo mail servers."""
        outgoing = self.sudo().mapped('mail_server_id')
        incoming = self.sudo().mapped('fetchmail_server_id')
        result = super(EmailAccount, self).unlink()
        if outgoing:
            outgoing.sudo().write({'active': False})
        if incoming:
            incoming.sudo().write({'active': False, 'state': 'draft'})
        return result

    @api.model
    def get_default_account(self):
        """Return the account other modules use when they do not specify one."""
        account = self.search([
            ('active', '=', True),
            ('is_default', '=', True),
        ], limit=1)
        if not account:
            account = self.search([('active', '=', True)], limit=1)
        if not account:
            raise UserError(_('Please set up an email account that is in use.'))
        return account

    @api.model
    def get_by_code(self, code):
        """Find the account by the stable code used by other modules."""
        account = self.search([
            ('code', '=', code),
            ('active', '=', True),
        ], limit=1)
        if not account:
            raise UserError(_('There is no active email account with code %s.') % code)
        return account

    def action_open_messages(self):
        """Open every message of this account."""
        self.ensure_one()
        return self._message_action(_('Messages of %s') % self.name, [])

    def action_open_errors(self):
        """Open the messages of this account that failed to send."""
        self.ensure_one()
        return self._message_action(
            _('Failures of %s') % self.name,
            [('state', '=', 'error')],
        )

    def _message_action(self, name, extra_domain):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'email.message',
            'view_mode': 'kanban,tree,form',
            'domain': [('account_id', '=', self.id)] + extra_domain,
            'context': {'default_account_id': self.id},
        }

    def action_test_smtp(self):
        """Log in to the SMTP server and report success to the user."""
        self.ensure_one()
        smtp = self._smtp_connect()
        try:
            smtp.noop()
        finally:
            try:
                smtp.quit()
            except Exception:
                _logger.debug('Failed to close the SMTP test session', exc_info=True)
        return self._notify(_('Sending confirmed'), _('The SMTP server accepted the login.'))

    def action_test_pop3(self):
        """Log in to the POP3 server and report success to the user."""
        self.ensure_one()
        conn = self._pop_connect()
        try:
            conn.user(self._pop_username())
            conn.pass_(self.pop3_password or '')
        finally:
            try:
                conn.quit()
            except Exception:
                _logger.debug('Failed to close the POP3 test session', exc_info=True)
        self._store_fetch_error(False)
        return self._notify(_('Receiving confirmed'), _('The POP3 server accepted the login.'))

    def _notify(self, title, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_fetch(self):
        """Download this account's POP3 mailbox now, if receiving is enabled."""
        created = self.sudo().fetch_incoming()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fetch completed'),
                'message': _(
                    'New messages: %s. They are in the Inbox.'
                ) % len(created),
                'type': 'success',
                'sticky': False,
            },
        }

    def send_for_record(self, res_model, res_id, email_to, subject, body,
                        email_cc=False, attachment_ids=None, body_format='text'):
        """Send an email linked to a record of another module."""
        self.ensure_one()
        return self.sudo()._send(
            email_to=email_to,
            subject=subject,
            body=body,
            res_model=res_model,
            res_id=res_id,
            email_cc=email_cc,
            attachment_ids=attachment_ids,
            body_format=body_format,
        )

    def fetch_incoming(self):
        """Download new messages over POP3 without deleting anything on the server."""
        created = self.env['email.message']
        for account in self:
            created |= account._fetch_one()
        return created

    def _fetch_one(self):
        self.ensure_one()
        if not self.pop_enabled:
            raise UserError(_('Enable receiving (POP) for this account.'))
        if not self.pop3_host:
            return self.env['email.message']
        conn = self._pop_connect()
        created = self.env['email.message']
        try:
            conn.user(self._pop_username())
            conn.pass_(self.pop3_password or '')
            _resp, listings, _oct = conn.uidl()
            known = set(self.uidl_ids.mapped('name'))
            for entry in listings:
                number, uidl = self._split_uidl(entry)
                if not uidl or uidl in known:
                    continue
                _retr_resp, lines, _retr_oct = conn.retr(int(number))
                parsed = self._parse_retrieved(lines)
                message = self._incoming_from_parsed(parsed)
                self.env['email.uidl'].create({
                    'account_id': self.id,
                    'name': uidl,
                })
                known.add(uidl)
                if message:
                    created |= message
            self.write({
                'last_fetch': fields.Datetime.now(),
                'last_fetch_error': False,
            })
        except Exception as exc:
            self._store_fetch_error(str(exc))
            raise
        finally:
            try:
                conn.quit()
            except Exception:
                _logger.debug('Failed to close the POP3 session', exc_info=True)
        return created

    def _store_fetch_error(self, error):
        # Written through a separate cursor and committed immediately: the
        # caller usually re-raises, which rolls back the current transaction,
        # and the error must still be visible on the account form afterwards.
        with self.pool.cursor() as cr:
            env = api.Environment(cr, self.env.uid, {})
            env['email.account'].browse(self.ids).write({
                'last_fetch': fields.Datetime.now(),
                'last_fetch_error': error or False,
            })
            cr.commit()

    def _pop_username(self):
        # After the first download Gmail hides already-fetched mail from POP3.
        # Logging in as "recent:<user>" makes Gmail return the last 30 days
        # instead, so messages are not lost; duplicates are filtered later.
        user = (self.pop3_user or '').strip()
        host = (self.pop3_host or '').lower()
        gmail = 'gmail.com' in host or 'googlemail.com' in host
        if user and gmail and not user.lower().startswith('recent:'):
            return 'recent:%s' % user
        return user

    def _incoming_from_parsed(self, parsed):
        # "recent:" mode may offer again a message that is already stored, but
        # under a different UIDL. The Message-ID is the reliable key, so a
        # message already saved for this account is skipped.
        message_id = self._normalize_msgid(parsed.get('Message-ID'))
        if message_id:
            existing = self.env['email.message'].search([
                ('account_id', '=', self.id),
                ('message_id', '=', message_id),
            ], limit=1)
            if existing:
                return self.env['email.message']
        return self._create_incoming(parsed)

    def _create_incoming(self, parsed):
        message_id = self._normalize_msgid(parsed.get('Message-ID'))
        in_reply_to = self._normalize_msgid(parsed.get('In-Reply-To'))
        date_value = self._message_date(parsed)
        parent = self._match_sent(parsed)
        matched = bool(parent)
        if not matched and self.only_replies and not self.keep_others:
            return self.env['email.message']
        message = self.env['email.message'].create({
            'account_id': self.id,
            'direction': 'in',
            'state': 'received',
            'in_inbox': matched or not self.only_replies,
            'message_id': message_id,
            'in_reply_to': in_reply_to,
            'subject': parsed.get('Subject') or '',
            'body': self._body_from_message(parsed),
            'email_from': parsed.get('From') or '',
            'email_to': parsed.get('To') or self.email,
            'email_cc': parsed.get('Cc') or False,
            'date': date_value,
            'parent_id': parent.id if parent else False,
            'res_model': parent.res_model if parent else False,
            'res_id': parent.res_id if parent else 0,
        })
        self._store_attachments(message, parsed)
        if matched:
            self._notify_origin(message, parent)
        return message

    def _match_sent(self, parsed):
        # Find the message we sent that is referenced by In-Reply-To or by any
        # entry of References. That link is what makes an incoming email a
        # "reply" and lets it inherit the originating record (res_model/res_id).
        wanted = []
        in_reply_to = self._normalize_msgid(parsed.get('In-Reply-To'))
        if in_reply_to:
            wanted.append(in_reply_to)
        for token in (parsed.get('References') or '').replace(',', ' ').split():
            normalized = self._normalize_msgid(token)
            if normalized and normalized not in wanted:
                wanted.append(normalized)
        if not wanted:
            return self.env['email.message']
        return self.env['email.message'].search([
            ('account_id', '=', self.id),
            ('direction', '=', 'out'),
            ('message_id', 'in', wanted),
        ], limit=1)

    def _notify_origin(self, message, parent):
        # Post a note and schedule an activity on the record that requested the
        # original email. Every step is guarded: a failure here (missing model,
        # no chatter, access issue) must never abort the whole POP3 fetch.
        if not parent.res_model or not parent.res_id:
            return
        try:
            record = self.env[parent.res_model].browse(parent.res_id).exists()
            if not record:
                return
            note = _('A reply arrived from %s: %s') % (
                message.email_from or _('unknown sender'),
                (message.preview or message.subject or '')[:240],
            )
            if hasattr(record, 'message_post'):
                try:
                    record.sudo().message_post(
                        body=note,
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                        email_from=message.email_from or 'ti@localhost',
                    )
                except Exception:
                    _logger.exception(
                        'Failed to log the reply on record %s', parent.res_model,
                    )
            user = record.create_uid
            if 'requested_by' in record._fields and record.requested_by:
                user = record.requested_by
            if user and hasattr(record, 'activity_schedule'):
                try:
                    record.sudo().activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary=_('Email reply: %s') % (message.subject or ''),
                        note=note,
                    )
                except Exception:
                    _logger.exception(
                        'Failed to notify the requester of record %s', parent.res_model,
                    )
        except Exception:
            _logger.exception('Failed to notify the origin record of message %s', message.id)

    def action_send_test(self):
        """Send a short email, with the banner, to the account itself to check sending."""
        self.ensure_one()
        self._send(
            email_to=self.email,
            subject=_('Sending test'),
            body=_(
                '<p>This is a test email from account %s.</p>'
                '<p>If a banner is set up, it appears at the end.</p>'
            ) % escape(self.email or ''),
            body_format='html',
        )
        return self._notify(
            _('Test sent'),
            _('The message was sent to %s. Check that mailbox.') % self.email,
        )

    def _store_attachments(self, message, parsed):
        if not getattr(parsed, 'is_multipart', lambda: False)():
            return
        Attachment = self.env['ir.attachment'].sudo()
        for part in parsed.walk():
            filename = part.get_filename()
            if not filename:
                continue
            payload = part.get_payload(decode=True) or b''
            attachment = Attachment.create({
                'name': filename,
                'datas': base64.b64encode(payload),
                'res_model': 'email.message',
                'res_id': message.id,
                'mimetype': part.get_content_type(),
            })
            message.attachment_ids = [(4, attachment.id)]

    def _banner_mime(self):
        ext = (self.signature_filename or 'png').rsplit('.', 1)[-1].lower()
        return _BANNER_EXT.get(ext, 'image/png')

    def _message_preview_html(self, body, body_format='text'):
        # Build an HTML preview of what the recipient will read, with the
        # banner appended. Plain text is escaped and kept with its line breaks;
        # the banner is inlined as a data URI because no MIME part exists yet.
        account = self[:1]
        if body_format == 'html':
            html = body or ''
        else:
            html = '<div style="white-space:pre-wrap;font-family:sans-serif;">%s</div>' % escape(body or '')
        if account and account.signature_image:
            raw = account.signature_image
            if isinstance(raw, bytes):
                raw = raw.decode('ascii')
            html += '<p><img src="data:%s;base64,%s" alt="Signature" style="max-width:100%%;"/></p>' % (
                account._banner_mime(), raw,
            )
        return html

    def _link_attachments(self, message, attachment_ids):
        attachments = self.env['ir.attachment'].browse(attachment_ids or []).exists()
        if not attachments:
            return
        for attachment in attachments:
            if attachment.res_model in (False, 'email.compose'):
                attachment.sudo().write({
                    'res_model': 'email.message',
                    'res_id': message.id,
                })
        message.attachment_ids = [(6, 0, attachments.ids)]

    def _send(self, email_to, subject, body, parent=None, res_model=False,
              res_id=0, in_reply_to=False, raise_on_error=True,
              email_cc=False, attachment_ids=None, deliver=True, template=None,
              body_format='text'):
        self.ensure_one()
        if deliver and not self.smtp_enabled:
            raise UserError(_('Enable sending (SMTP) for this account.'))
        parent = parent or self.env['email.message']
        if parent and not in_reply_to:
            in_reply_to = parent.message_id
        msgid = self._new_message_id()
        message = self.env['email.message'].create({
            'account_id': self.id,
            'direction': 'out',
            'state': 'draft',
            'message_id': msgid,
            'in_reply_to': in_reply_to or False,
            'subject': subject or '',
            'body': body or '',
            'body_format': body_format or 'text',
            'email_from': self.email,
            'email_to': email_to,
            'email_cc': email_cc or False,
            'date': fields.Datetime.now(),
            'parent_id': parent.id if parent else False,
            'res_model': res_model or (parent.res_model if parent else False),
            'res_id': res_id or (parent.res_id if parent else 0),
            'template_id': template.id if template else False,
        })
        self._link_attachments(message, attachment_ids)
        if not deliver:
            return message
        try:
            self._smtp_deliver(message)
        except Exception as exc:
            message.write({'state': 'error', 'error_message': str(exc)})
            _logger.exception('Failed to send email through account %s', self.email)
            if raise_on_error:
                raise UserError(_('Sending failed: %s') % exc)
            return message
        message.state = 'sent'
        return message

    def _smtp_deliver(self, message):
        if not self.smtp_enabled:
            raise UserError(_('Enable sending (SMTP) for this account.'))
        mime = EmailMessage()
        mime['Subject'] = message.subject or ''
        mime['From'] = self.email
        mime['To'] = message.email_to
        if message.email_cc:
            mime['Cc'] = message.email_cc
        mime['Message-ID'] = message.message_id
        if message.in_reply_to:
            mime['In-Reply-To'] = message.in_reply_to
            mime['References'] = message.in_reply_to
        self._fill_mime_body(mime, message)
        for attachment in message.attachment_ids:
            if not attachment.datas:
                continue
            mimetype = attachment.mimetype or 'application/octet-stream'
            maintype, _sep, subtype = mimetype.partition('/')
            mime.add_attachment(
                base64.b64decode(attachment.datas),
                maintype=maintype or 'application',
                subtype=subtype or 'octet-stream',
                filename=attachment.name or 'attachment',
            )
        smtp = self._smtp_connect()
        try:
            smtp.send_message(mime)
        finally:
            try:
                smtp.quit()
            except Exception:
                _logger.debug('Failed to close the SMTP session', exc_info=True)

    def _fill_mime_body(self, mime, message):
        # Always provide a plain-text part. An HTML alternative is added when
        # the body is HTML, or when a banner exists (the banner needs HTML to
        # be displayed). The banner itself is attached as an inline related
        # image referenced by "cid:assinatura" so mail clients show it offline.
        plain = message.body or ''
        html_body = False
        if message.body_format == 'html':
            html_body = plain
            plain = re.sub(r'<[^>]+>', ' ', plain)
            plain = re.sub(r'\s+', ' ', plain).strip()
        elif self.signature_image:
            html_body = '<div style="white-space:pre-wrap;">%s</div>' % escape(message.body or '')
        if self.signature_image:
            html_body = (html_body or '') + '<p><img src="cid:assinatura" alt="Signature" style="max-width:100%;"/></p>'
        mime.set_content(plain or '')
        if html_body:
            mime.add_alternative(html_body, subtype='html')
        if self.signature_image and html_body:
            raw = base64.b64decode(self.signature_image)
            maintype, _sep, subtype = self._banner_mime().partition('/')
            html_part = mime.get_body(preferencelist=('html',))
            html_part.add_related(
                raw,
                maintype=maintype or 'image',
                subtype=subtype or 'png',
                cid='assinatura',
                disposition='inline',
                filename=self.signature_filename or 'banner.png',
            )

    def _smtp_connect(self):
        # Module updates run with tests enabled against the real database.
        # Without this guard, the tests would open real SMTP connections and
        # send real emails from the configured accounts.
        if config.get('test_enable'):
            return _SmtpMudo()
        if not self.smtp_enabled:
            raise UserError(_('Enable sending (SMTP) for this account.'))
        if not self.smtp_host:
            raise UserError(_('This account has no outgoing server. Choose the provider.'))
        if self.smtp_ssl:
            smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port or 465, timeout=30)
        else:
            smtp = smtplib.SMTP(self.smtp_host, self.smtp_port or 587, timeout=30)
            if self.smtp_tls:
                smtp.starttls()
        if self.smtp_user:
            smtp.login(self.smtp_user, self.smtp_password or '')
        return smtp

    def _pop_connect(self):
        if not self.pop_enabled:
            raise UserError(_('Enable receiving (POP) for this account.'))
        if not self.pop3_host:
            raise UserError(_('This account has no incoming server. Choose the provider.'))
        port = self.pop3_port or (995 if self.pop3_ssl else 110)
        if self.pop3_ssl:
            return poplib.POP3_SSL(self.pop3_host, port, timeout=30)
        return poplib.POP3(self.pop3_host, port, timeout=30)

    @api.model
    def cron_fetch_all(self):
        """Fetch every active POP-enabled account; one failure does not stop the others."""
        accounts = self.search([
            ('active', '=', True),
            ('pop_enabled', '=', True),
            ('pop3_host', '!=', False),
        ])
        for account in accounts:
            try:
                account.sudo().fetch_incoming()
            except Exception:
                _logger.exception('Failed to fetch account %s', account.email)

    def _new_message_id(self):
        domain = (self.email or 'local').split('@')[-1]
        return '<%s@%s>' % (uuid4().hex, domain)

    @api.model
    def _normalize_msgid(self, value):
        if not value:
            return False
        value = value.strip()
        if value.startswith('<') and value.endswith('>'):
            return value
        return '<%s>' % value.strip('<>')

    @api.model
    def _split_uidl(self, entry):
        if isinstance(entry, bytes):
            entry = entry.decode('utf-8', errors='replace')
        parts = (entry or '').split()
        if len(parts) < 2:
            return False, False
        return parts[0], parts[1]

    @api.model
    def _parse_retrieved(self, lines):
        if lines and isinstance(lines[0], bytes):
            raw = b'\r\n'.join(lines)
        else:
            raw = '\r\n'.join(lines).encode('utf-8', errors='replace')
        return BytesParser(policy=default).parsebytes(raw)

    @api.model
    def _body_from_message(self, parsed):
        if parsed.is_multipart():
            for part in parsed.walk():
                if part.get_content_type() == 'text/plain' and not part.get_filename():
                    return self._decode_part(part)
            for part in parsed.walk():
                if part.get_content_type() == 'text/html' and not part.get_filename():
                    return self._decode_part(part)
            return ''
        return self._decode_part(parsed)

    @api.model
    def _decode_part(self, part):
        payload = part.get_payload(decode=True) or b''
        charset = part.get_content_charset() or 'utf-8'
        return payload.decode(charset, errors='replace')

    @api.model
    def _message_date(self, parsed):
        raw = parsed.get('Date')
        if not raw:
            return fields.Datetime.now()
        try:
            moment = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return fields.Datetime.now()
        if moment.tzinfo:
            moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
        if not isinstance(moment, datetime):
            return fields.Datetime.now()
        return moment


class EmailUidl(models.Model):
    _name = 'email.uidl'
    _description = 'Downloaded UIDL'
    _rec_name = 'name'

    account_id = fields.Many2one(
        'email.account', required=True, ondelete='cascade', index=True,
    )
    name = fields.Char(string='UIDL', required=True, index=True)

    _sql_constraints = [
        (
            'email_uidl_unique',
            'unique(account_id, name)',
            'This UIDL has already been downloaded for this account.',
        ),
    ]

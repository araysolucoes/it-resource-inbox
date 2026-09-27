# -*- coding: utf-8 -*-
"""Receipt and return terms, the places marked on PDF terms and the signatures.

When a resource is delivered or returned, each request line produces a
signature record holding a frozen copy of the term. The copy keeps the signed
text intact even if the term is edited later.
"""
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


class ItResourceTerm(models.Model):
    """Term text (or PDF) signed on delivery or on return."""

    _name = 'it.resource.term'
    _description = 'Receipt or return term'
    _order = 'term_type, name'

    name = fields.Char(string='Term name', required=True)
    term_type = fields.Selection(
        [('receipt', 'Receipt'), ('return', 'Return')],
        string='When it is used',
        required=True,
        help='Receipt is signed on delivery. Return is signed when the resource comes back.',
    )
    mode = fields.Selection(
        [('text', 'Text and signature'), ('pdf', 'PDF with marked places')],
        string='Term format',
        required=True,
        default='text',
        help='Text: you write the term and the person only draws the signature. PDF: you upload the file and mark where the data and the signature go.',
    )
    body = fields.Text(
        string='Term text',
        help='Use {{colaborador}}, {{necessidade}}, {{item}}, {{quantidade}}, {{data}}, {{solicitante}} and {{pedido}}.',
    )
    pdf_file = fields.Binary(string='PDF file', attachment=True)
    pdf_name = fields.Char(string='PDF name')
    is_default = fields.Boolean(
        string='Term used in requests',
        help='Requests use the marked term. Only one of each type stays marked.',
    )
    active = fields.Boolean(string='Active', default=True)
    place_ids = fields.One2many(
        'it.resource.term.place',
        'term_id',
        string='Places in the PDF',
    )

    @api.model
    def get_default(self, term_type):
        """Return the active default term of the given type or explain how to set one."""
        term = self.search([
            ('term_type', '=', term_type),
            ('is_default', '=', True),
            ('active', '=', True),
        ], limit=1)
        if not term:
            raise UserError(_(
                'In Settings, Signature terms, mark a %s term as the one used in requests.'
            ) % dict(self._fields['term_type'].selection)[term_type])
        return term

    def write(self, vals):
        """Save terms, keeping a single default term per type."""
        result = super(ItResourceTerm, self).write(vals)
        if vals.get('is_default'):
            for term in self.filtered('is_default'):
                others = self.search([
                    ('id', '!=', term.id),
                    ('term_type', '=', term.term_type),
                    ('is_default', '=', True),
                ])
                if others:
                    others.write({'is_default': False})
        return result

    def render_body(self, line):
        """Replace the term placeholders with the data of a request line.

        The placeholder keys are Portuguese because existing terms stored in
        the database use them; renaming would break those texts.
        """
        self.ensure_one()
        values = {
            'colaborador': line.collaborator_id.name or '',
            'necessidade': line.need_id.name or '',
            'item': line.item_id.name or '',
            'quantidade': line.quantity or '',
            'data': fields.Date.context_today(self),
            'solicitante': line.request_id.requested_by.name or '',
            'pedido': line.request_id.name or '',
        }
        text = self.body or ''
        for key, value in values.items():
            text = text.replace('{{%s}}' % key, str(value))
        return text

    def render_places(self, line):
        """Describe, one per line, what goes into each marked place of the PDF."""
        self.ensure_one()
        rendered = self.render_body(line)
        rows = []
        for place in self.place_ids:
            rows.append(place._describe(line, rendered))
        return '\n'.join(rows)


class ItResourceTermPlace(models.Model):
    """Rectangle on a PDF page, in percentages, where a piece of data is placed."""

    _name = 'it.resource.term.place'
    _description = 'Place marked on the term PDF'
    _order = 'page, pos_y, pos_x, id'

    term_id = fields.Many2one(
        'it.resource.term',
        required=True,
        ondelete='cascade',
    )
    page = fields.Integer(
        string='Page',
        default=1,
        required=True,
        help='PDF page number, starting at 1.',
    )
    role = fields.Selection(
        [
            ('colaborador', 'Collaborator name'),
            ('necessidade', 'Need'),
            ('item', 'Chosen item'),
            ('quantidade', 'Quantity'),
            ('data', 'Date'),
            ('solicitante', 'Requested by'),
            ('pedido', 'Request number'),
            ('assinatura', 'Signature'),
            ('texto', 'Term text'),
        ],
        string='What goes in this place',
        required=True,
    )
    pos_x = fields.Float(
        string='From the left (%)',
        help='0 is the left edge of the page. 50 is the middle.',
    )
    pos_y = fields.Float(
        string='From the top (%)',
        help='0 is the top of the page. 50 is the middle.',
    )
    width = fields.Float(string='Width (%)', default=30)
    height = fields.Float(string='Height (%)', default=8)

    def _describe(self, line, rendered_text):
        self.ensure_one()
        values = {
            'colaborador': line.collaborator_id.name or '',
            'necessidade': line.need_id.name or '',
            'item': line.item_id.name or '',
            'quantidade': str(line.quantity or ''),
            'data': str(fields.Date.context_today(self)),
            'solicitante': line.request_id.requested_by.name or '',
            'pedido': line.request_id.name or '',
            'texto': rendered_text,
            'assinatura': _('Signature drawn on screen'),
        }
        label = dict(self._fields['role'].selection)[self.role]
        return _(
            'Page %(page)s, %(x)s%% from the left and %(y)s%% from the top: %(label)s = %(value)s'
        ) % {
            'page': self.page,
            'x': self.pos_x,
            'y': self.pos_y,
            'label': label,
            'value': values.get(self.role, ''),
        }


class ItResourceSignature(models.Model):
    """Signature of one request line on a term, with a snapshot of the signed text."""

    _name = 'it.resource.signature'
    _description = 'IT term signature'
    _order = 'id desc'

    request_id = fields.Many2one(
        'it.resource.request',
        string='Request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    line_id = fields.Many2one(
        'it.resource.request.line',
        string='Request need',
        required=True,
        ondelete='cascade',
    )
    term_id = fields.Many2one(
        'it.resource.term',
        string='Term',
        required=True,
        ondelete='restrict',
    )
    term_type = fields.Selection(related='term_id.term_type', store=True, string='Type')
    signer_id = fields.Many2one(
        'res.users',
        string='Signer',
        required=True,
    )
    state = fields.Selection(
        [('pending', 'Waiting for signature'), ('signed', 'Signed')],
        string='Status',
        default='pending',
        required=True,
    )
    body_snapshot = fields.Text(
        string='Presented text',
        readonly=True,
        help='Copy of the term at the moment the signature was requested.',
    )
    place_snapshot = fields.Text(
        string='PDF places',
        readonly=True,
    )
    pdf_file = fields.Binary(string='Term PDF', attachment=True, readonly=True)
    pdf_name = fields.Char(string='PDF name')
    signature = fields.Binary(
        string='Signature',
        attachment=True,
        help='Draw the signature in the area below. It is stored on this term.',
    )
    signed_on = fields.Datetime(string='Signed on', readonly=True)

    def action_sign(self):
        """Confirm the drawn signature and advance the request when all lines are signed."""
        for sign in self:
            user = self.env.user
            if user.id != SUPERUSER_ID and user != sign.signer_id and not user.has_group(
                'it_resource_request.group_it_resource_manager'
            ):
                raise UserError(_('Only the collaborator of this line, or the manager, can sign this term.'))
            if sign.state != 'pending':
                raise UserError(_('This term has already been signed.'))
            if not sign.signature:
                raise UserError(_('Draw the signature before confirming.'))
            sign.write({
                'state': 'signed',
                'signed_on': fields.Datetime.now(),
            })
            sign.request_id._after_signature(sign)
        return self[:1].request_id._open_stage()

    @api.model
    def create_for_lines(self, lines, term_type):
        """Create one pending signature per line using the default term of the type."""
        term = self.env['it.resource.term'].get_default(term_type)
        created = self.browse()
        for line in lines:
            signer = line.collaborator_id or line.request_id.requested_by
            if not signer:
                raise UserError(_('Set the collaborator who will sign.'))
            values = {
                'request_id': line.request_id.id,
                'line_id': line.id,
                'term_id': term.id,
                'signer_id': signer.id,
                'body_snapshot': term.render_body(line),
                'place_snapshot': term.render_places(line) if term.mode == 'pdf' else False,
                'pdf_name': term.pdf_name if term.mode == 'pdf' else False,
            }
            if term.mode == 'pdf' and term.pdf_file:
                values['pdf_file'] = term.pdf_file
            created |= self.create(values)
        return created

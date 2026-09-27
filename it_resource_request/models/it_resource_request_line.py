# -*- coding: utf-8 -*-
"""Lines of an IT resource request: one need, its recipient and the chosen item.

The line is where the abstract need (what the person asks for) meets the
concrete catalog item (what IT delivers). Fulfilling a line moves stock or
reserves units and creates the assignment records.
"""
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


class ItResourceRequestLine(models.Model):
    """One need of a request, later matched to a catalog item during allocation."""

    _name = 'it.resource.request.line'
    _description = 'IT resource request line'
    _order = 'id'

    request_id = fields.Many2one(
        'it.resource.request',
        string='Request',
        required=True,
        ondelete='cascade',
    )
    need_id = fields.Many2one(
        'it.resource.need',
        string='Need',
        ondelete='restrict',
        domain=[('active', '=', True)],
        help='What the collaborator needs. The exact item is chosen during allocation, by the approvers and by IT.',
    )
    collaborator_id = fields.Many2one(
        'res.users',
        string='Collaborator',
        help='Person who receives and signs. When empty, the collaborator of the request is used.',
    )
    item_id = fields.Many2one(
        'it.resource.item',
        string='Chosen item',
        ondelete='restrict',
        help='Filled during allocation. It is the product, license or access that meets the need.',
    )
    availability = fields.Selection(
        [
            ('pending', 'Not checked yet'),
            ('ok', 'In stock'),
            ('short', 'Out of stock'),
        ],
        string='Availability',
        default='pending',
        help='Result of the stock check after the item was chosen.',
    )
    fulfilled = fields.Boolean(
        string='Delivered from stock',
        default=False,
        help='Checked when the receipt signature reduced the stock or reserved the unit.',
    )
    tracking = fields.Selection(
        related='item_id.tracking',
        string='Item tracking',
    )
    qty_available = fields.Float(
        related='item_id.qty_available',
        string='Available now',
    )
    quantity = fields.Float(
        string='Requested quantity',
        required=True,
        default=1.0,
        help='For quantity tracking, it is the amount to deduct. For unit tracking, it is the number of serials, keys or users.',
    )
    expected_date = fields.Datetime(
        string='Needed by',
        help='When empty, the request header date is copied.',
    )
    assignee_id = fields.Many2one(
        'res.users',
        string='Recipient',
        help='Person who keeps the item. When empty, the requester is used.',
    )
    unit_ids = fields.Many2many(
        'it.resource.unit',
        'it_resource_line_unit_rel',
        'line_id',
        'unit_id',
        string='Units',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('open', 'In progress'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
    )
    assignment_ids = fields.One2many(
        'it.resource.assignment', 'line_id', string='Assignments',
    )

    @api.onchange('request_id')
    def _onchange_request_id(self):
        if self.request_id and not self.assignee_id:
            self.assignee_id = self.request_id.requested_by
        if self.request_id and not self.expected_date:
            self.expected_date = self.request_id.expected_date

    @api.model_create_multi
    def create(self, vals_list):
        """Default the recipient and date from the request header.

        Lines created by code (``request_for``) never run the onchange, so the
        same defaults are applied here to keep both paths consistent.
        """
        for vals in vals_list:
            request = self.env['it.resource.request'].browse(vals.get('request_id'))
            if request:
                collaborator = vals.get('collaborator_id') or request.collaborator_id.id
                if collaborator:
                    vals.setdefault('collaborator_id', collaborator)
                    vals.setdefault('assignee_id', collaborator)
                else:
                    vals.setdefault('assignee_id', request.requested_by.id)
                vals.setdefault('expected_date', request.expected_date)
        return super().create(vals_list)

    def _check_manager(self):
        # The internal Odoo superuser (id 1) belongs to no group, yet it must
        # be able to fulfill lines when the signature flow runs in sudo.
        user = self.env.user
        if user.id != SUPERUSER_ID and not user.has_group(
            'it_resource_request.group_it_resource_manager'
        ):
            raise UserError(_('Only the manager can fulfill a request.'))

    def action_confirm(self):
        """Move draft lines to in progress."""
        for line in self:
            if line.state != 'draft':
                raise UserError(_('Only a draft line can be confirmed.'))
        self.write({'state': 'open'})
        return True

    def action_cancel(self):
        """Cancel draft or in-progress lines."""
        for line in self:
            if line.state not in ('draft', 'open'):
                raise UserError(_('Only a draft or in-progress line can be cancelled.'))
        self.write({'state': 'cancel'})
        return True

    def action_draft(self):
        """Reset cancelled lines to draft."""
        for line in self:
            if line.state != 'cancel':
                raise UserError(_('Only a cancelled line can be reset to draft.'))
        self.write({'state': 'draft'})
        return True

    def action_fulfill(self):
        """Deliver the chosen item of each line to its recipient (managers only)."""
        self._check_manager()
        for line in self:
            line._fulfill_one()
        return True

    def _fulfill_one(self):
        # Idempotent on purpose: the receipt signature may trigger it again for
        # a line already fulfilled manually, and stock must not move twice.
        self.ensure_one()
        if self.fulfilled:
            return True
        if not self.item_id:
            raise UserError(_('Choose the item before delivering.'))
        if self.quantity <= 0:
            raise UserError(_('The quantity must be greater than zero.'))
        assignee = self.collaborator_id or self.assignee_id or self.request_id.requested_by
        if not assignee:
            raise UserError(_('Set the collaborator who receives the item.'))
        if self.item_id.tracking == 'quantity':
            self._fulfill_quantity(assignee)
        else:
            self._fulfill_units(assignee)
        self.write({
            'state': 'done',
            'fulfilled': True,
            'assignee_id': assignee.id,
            'collaborator_id': assignee.id,
        })
        self.request_id.message_post(body=_(
            'Line fulfilled: %(item)s for %(user)s.'
        ) % {'item': self.item_id.name, 'user': assignee.name})

    def _fulfill_quantity(self, assignee):
        item = self.item_id
        if item.qty_on_hand < self.quantity:
            raise UserError(_('Not enough stock of %s.') % item.name)
        item.qty_on_hand -= self.quantity
        self.env['it.resource.assignment'].create({
            'item_id': item.id,
            'user_id': assignee.id,
            'quantity': self.quantity,
            'line_id': self.id,
        })

    def _fulfill_units(self, assignee):
        # Each unit (serial, key, VPN login) is a single record, so the quantity
        # must be a whole number. When IT did not pick units by hand, the first
        # free ones of the item are taken.
        if self.quantity != int(self.quantity):
            raise UserError(_('With unit tracking, the quantity must be a whole number.'))
        units = self.unit_ids
        if not units:
            units = self.env['it.resource.unit'].search([
                ('item_id', '=', self.item_id.id),
                ('state', '=', 'available'),
            ], limit=int(self.quantity))
        if len(units) != int(self.quantity):
            raise UserError(_('Select free units matching the requested quantity.'))
        if any(unit.state != 'available' or unit.item_id != self.item_id for unit in units):
            raise UserError(_('There is a unit that is unavailable or belongs to another item.'))
        units.write({
            'state': 'assigned',
            'assigned_user_id': assignee.id,
            'assigned_line_id': self.id,
        })
        for unit in units:
            self.env['it.resource.assignment'].create({
                'item_id': self.item_id.id,
                'user_id': assignee.id,
                'quantity': 1.0,
                'line_id': self.id,
                'unit_id': unit.id,
            })
        self.unit_ids = units

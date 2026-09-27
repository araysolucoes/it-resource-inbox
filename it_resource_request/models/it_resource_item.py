# -*- coding: utf-8 -*-
"""Catalog items delivered by IT (equipment, VPN, licenses).

The module keeps its own lightweight stock instead of depending on the Odoo
inventory: an item is either counted by quantity or tracked unit by unit.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItResourceItem(models.Model):
    """Concrete product, license or access that fulfills a need."""

    _name = 'it.resource.item'
    _description = 'IT resource item'
    _order = 'name'

    name = fields.Char(
        string='Item name',
        required=True,
        help='Name shown on the request. Example: Mouse, Corporate VPN, Office license.',
    )
    code = fields.Char(
        string='Code for other modules',
        copy=False,
        help='Stable name without spaces. Other modules request the item by this code. Example: mouse or vpn_corp.',
    )
    item_type = fields.Selection(
        [('physical', 'Physical'), ('virtual', 'Virtual')],
        string='Type',
        required=True,
        default='physical',
        help='Physical is an object. Virtual is an access, license or VPN.',
    )
    category = fields.Selection(
        [
            ('equipment', 'Equipment'),
            ('vpn', 'VPN'),
            ('license', 'License'),
            ('other', 'Other'),
        ],
        string='Category',
        required=True,
        default='equipment',
        help='Groups the item in the catalog. It does not change the stock.',
    )
    # "quantity" keeps a plain number; "unit" keeps one record per serial
    # number, license key or VPN user, so each one can be traced to a person.
    tracking = fields.Selection(
        [('quantity', 'By quantity'), ('unit', 'By unit')],
        string='How stock is counted',
        required=True,
        default='quantity',
        help='By quantity: a number that decreases when fulfilled. By unit: each serial, key or VPN user is a record.',
    )
    qty_on_hand = fields.Float(
        string='Quantity on hand',
        default=0.0,
        help='Only used with quantity tracking. Fulfilling a request decreases this number. Returning increases it.',
    )
    qty_available = fields.Float(
        string='Available now',
        compute='_compute_qty_available',
        store=True,
        help='With quantity tracking, it is the number on hand. With unit tracking, it is the number of free units.',
    )
    is_short = fields.Boolean(
        string='Out of stock',
        compute='_compute_qty_available',
        store=True,
    )
    description = fields.Text(
        string='What it is for',
        help='Free text so whoever requests the item knows what they will receive.',
    )
    active = fields.Boolean(
        string='Item in use',
        default=True,
        help='When unchecked, the item leaves the lists and can no longer be requested.',
    )

    _sql_constraints = [
        (
            'it_resource_item_code_unique',
            'unique(code)',
            'An item with this code already exists.',
        ),
    ]
    unit_ids = fields.One2many('it.resource.unit', 'item_id', string='Units')
    assignment_ids = fields.One2many(
        'it.resource.assignment', 'item_id', string='Assignments',
    )

    @api.depends('tracking', 'qty_on_hand', 'unit_ids.state')
    def _compute_qty_available(self):
        unit_model = self.env['it.resource.unit']
        for item in self:
            if item.tracking == 'quantity':
                item.qty_available = item.qty_on_hand
            else:
                item.qty_available = unit_model.search_count([
                    ('item_id', '=', item.id),
                    ('state', '=', 'available'),
                ])
            item.is_short = item.qty_available <= 0

    @api.model
    def get_by_code(self, code):
        """Return the active item another module asks for by its stable code."""
        item = self.search([('code', '=', code), ('active', '=', True)], limit=1)
        if not item:
            raise UserError(_('There is no active IT item with code %s.') % code)
        return item

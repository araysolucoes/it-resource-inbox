# -*- coding: utf-8 -*-
"""Individually tracked units of an item (serial number, license key, VPN login)."""
from odoo import fields, models


class ItResourceUnit(models.Model):
    """Single physical or virtual piece that can be assigned to one person."""

    _name = 'it.resource.unit'
    _description = 'IT resource unit'
    _order = 'name'

    name = fields.Char(
        string='Serial, key or user',
        required=True,
        help='Serial number of the equipment, license key or VPN login.',
    )
    item_id = fields.Many2one(
        'it.resource.item',
        string='Item',
        required=True,
        ondelete='restrict',
        domain=[('tracking', '=', 'unit')],
    )
    state = fields.Selection(
        [('available', 'Available'), ('assigned', 'Assigned')],
        string='Status',
        default='available',
        required=True,
    )
    assigned_user_id = fields.Many2one('res.users', string='Assigned to')
    assigned_line_id = fields.Many2one(
        'it.resource.request.line',
        string='Request line',
        ondelete='set null',
    )

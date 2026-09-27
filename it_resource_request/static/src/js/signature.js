odoo.define('it_resource_request.signature_widget', function (require) {
    'use strict';

    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');

    // Signature pad for binary fields. The canvas is built inside _render
    // because the default field render empties the element, which would wipe
    // a canvas coming from a QWeb template. The drawing is stored as a PNG
    // (base64, without the data URL prefix) in the binary field.
    var SignatureField = AbstractField.extend({
        supportedFieldTypes: ['binary'],
        events: {
            'mousedown .o_it_sign_pad': '_onDown',
            'mousemove .o_it_sign_pad': '_onMove',
            'mouseup .o_it_sign_pad': '_onUp',
            'mouseleave .o_it_sign_pad': '_onUp',
            'touchstart .o_it_sign_pad': '_onDown',
            'touchmove .o_it_sign_pad': '_onMove',
            'touchend .o_it_sign_pad': '_onUp',
            'click .o_it_sign_clear': '_onClear',
        },
        _render: function () {
            var self = this;
            this.$el.empty().addClass('o_it_sign');
            var canvas = document.createElement('canvas');
            canvas.className = 'o_it_sign_pad';
            canvas.width = 520;
            canvas.height = 160;
            this.el.appendChild(canvas);
            this.canvas = canvas;
            this.ctx = canvas.getContext('2d');
            this.ctx.lineWidth = 2;
            this.ctx.lineCap = 'round';
            this.ctx.strokeStyle = '#1d1a1f';
            this._drawing = false;
            // In readonly mode the saved signature is only displayed, so the
            // canvas ignores pointer events and no clear button is offered.
            if (this.mode === 'readonly') {
                canvas.style.pointerEvents = 'none';
            } else {
                var button = document.createElement('button');
                button.type = 'button';
                button.className = 'btn btn-secondary o_it_sign_clear';
                button.textContent = 'Clear signature';
                this.el.appendChild(button);
            }
            if (this.value && typeof this.value === 'string') {
                var img = new Image();
                img.onload = function () {
                    if (self.ctx && self.canvas) {
                        self.ctx.drawImage(img, 0, 0, self.canvas.width, self.canvas.height);
                    }
                };
                img.src = 'data:image/png;base64,' + this.value;
            }
            return Promise.resolve();
        },
        // Converts the pointer position to canvas coordinates. The canvas is
        // scaled by CSS (width: 100%), so the ratio between its internal size
        // and its displayed size must be applied for the stroke to follow the
        // pointer. Touch events carry the position in ev.touches.
        _pos: function (ev) {
            var rect = this.canvas.getBoundingClientRect();
            var point = ev.touches ? ev.touches[0] : ev;
            return {
                x: (point.clientX - rect.left) * (this.canvas.width / rect.width),
                y: (point.clientY - rect.top) * (this.canvas.height / rect.height),
            };
        },
        _onDown: function (ev) {
            if (this.mode === 'readonly' || !this.ctx) {
                return;
            }
            ev.preventDefault();
            this._drawing = true;
            var point = this._pos(ev);
            this.ctx.beginPath();
            this.ctx.moveTo(point.x, point.y);
        },
        _onMove: function (ev) {
            if (!this._drawing || !this.ctx) {
                return;
            }
            ev.preventDefault();
            var point = this._pos(ev);
            this.ctx.lineTo(point.x, point.y);
            this.ctx.stroke();
        },
        // The value is saved once per stroke, when the pointer is released,
        // instead of on every move, to avoid flooding the record with changes.
        _onUp: function (ev) {
            if (!this._drawing || !this.canvas) {
                return;
            }
            ev.preventDefault();
            this._drawing = false;
            var data = this.canvas.toDataURL('image/png');
            this._setValue(data.split(',')[1]);
        },
        _onClear: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            if (!this.ctx || !this.canvas) {
                return;
            }
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this._setValue(false);
        },
    });

    fieldRegistry.add('it_signature', SignatureField);
});

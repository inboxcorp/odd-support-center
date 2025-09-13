# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AppointmentSuggestions(models.TransientModel):
    _name = 'support.appointment.suggestions'
    _description = 'Appointment Time Suggestions'

    wizard_id = fields.Many2one(
        'support.appointment.wizard',
        string='Original Wizard',
        required=True
    )
    technician_name = fields.Char(
        string='Technician',
        related='wizard_id.technician_id.name',
        readonly=True
    )
    selected_datetime = fields.Selection(
        selection='_get_time_suggestions',
        string='Available Times'
    )

    @api.model
    def _get_time_suggestions(self):
        """Get available time suggestions from context"""
        suggestions = self.env.context.get('default_suggestions', [])
        return [(s['datetime'].isoformat(), s['display_name']) for s in suggestions]

    def action_select_time(self):
        """Apply selected time to the original wizard"""
        if not self.selected_datetime:
            raise UserError(_('Please select a time slot.'))
        
        # Update the original wizard with the selected time
        selected_datetime = fields.Datetime.from_string(self.selected_datetime)
        self.wizard_id.write({
            'scheduled_date': selected_datetime,
        })
        
        # Trigger conflict check
        self.wizard_id._onchange_check_conflicts()
        
        # Return to the original wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Appointment'),
            'res_model': 'support.appointment.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
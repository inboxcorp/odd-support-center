# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AppointmentQuickCreateWizard(models.TransientModel):
    _name = 'support.appointment.wizard'
    _description = 'Quick Create Appointment Wizard'

    # Basic appointment info
    customer_id = fields.Many2one(
        'res.partner', 
        string='Customer', 
        required=True,
        help="Select or create a customer for this appointment"
    )
    technician_id = fields.Many2one(
        'res.users', 
        string='Technician', 
        required=True,
        domain=[('groups_id', 'in', 'support_center.group_support_technician')],
        help="Assign a technician for this appointment"
    )
    scheduled_date = fields.Datetime(
        string='Scheduled Date & Time', 
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(hours=1)
    )
    duration = fields.Float(
        string='Duration (Hours)', 
        default=1.0,
        help="Estimated duration in hours"
    )
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='normal', string='Priority')
    
    description = fields.Text(
        string='Service Description',
        help="Describe the service or issue to be addressed"
    )
    location = fields.Char(
        string='Service Location',
        help="Where will the service take place?"
    )
    
    # Email options
    send_confirmation_email = fields.Boolean(
        string='Send Confirmation Email', 
        default=True,
        help="Automatically send confirmation email to customer"
    )
    send_reminder_email = fields.Boolean(
        string='Send Reminder Email', 
        default=True,
        help="Send reminder email 24 hours before appointment"
    )
    
    # Conflict checking
    conflicts_found = fields.Boolean(
        string='Conflicts Detected',
        default=False,
        readonly=True
    )
    conflict_message = fields.Text(
        string='Conflict Details',
        readonly=True
    )
    
    # Existing ticket option
    existing_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Link to Existing Ticket',
        help="Optionally link to an existing helpdesk ticket"
    )

    @api.onchange('technician_id', 'scheduled_date', 'duration')
    def _onchange_check_conflicts(self):
        """Check for scheduling conflicts when key fields change"""
        if self.technician_id and self.scheduled_date and self.duration:
            self._check_technician_availability()

    def _check_technician_availability(self):
        """Check if technician is available at the scheduled time"""
        self.conflicts_found = False
        self.conflict_message = False
        
        if not all([self.technician_id, self.scheduled_date, self.duration]):
            return
            
        end_datetime = self.scheduled_date + timedelta(hours=self.duration)
        
        # Search for conflicting appointments
        conflicts = self.env['support.appointment'].search([
            ('technician_id', '=', self.technician_id.id),
            ('scheduled_date', '<', end_datetime),
            ('end_datetime', '>', self.scheduled_date),
            ('status', 'in', ['confirmed', 'in_progress'])
        ])
        
        if conflicts:
            self.conflicts_found = True
            conflict_details = []
            for conflict in conflicts:
                conflict_details.append(
                    f"• {conflict.name}: {conflict.scheduled_date.strftime('%Y-%m-%d %H:%M')} - "
                    f"{conflict.end_datetime.strftime('%H:%M')} ({conflict.customer_id.name})"
                )
            
            self.conflict_message = "Scheduling conflicts detected:\n" + "\n".join(conflict_details)
            
            return {
                'warning': {
                    'title': _('Scheduling Conflict'),
                    'message': _(
                        'The selected technician has conflicting appointments at this time. '
                        'Please choose a different time or technician.'
                    )
                }
            }

    @api.onchange('customer_id')
    def _onchange_customer_prefill(self):
        """Prefill location from customer address when customer is selected"""
        if self.customer_id:
            # Use customer's address as default location
            address_parts = []
            if self.customer_id.street:
                address_parts.append(self.customer_id.street)
            if self.customer_id.street2:
                address_parts.append(self.customer_id.street2)
            if self.customer_id.city:
                address_parts.append(self.customer_id.city)
                
            if address_parts:
                self.location = ', '.join(address_parts)

    @api.onchange('scheduled_date')
    def _onchange_validate_date(self):
        """Validate that appointment is not scheduled in the past"""
        if self.scheduled_date and self.scheduled_date <= fields.Datetime.now():
            return {
                'warning': {
                    'title': _('Invalid Date'),
                    'message': _('Cannot schedule appointments in the past. Please select a future date and time.')
                }
            }

    def action_create_appointment(self):
        """Create the appointment with validation"""
        self.ensure_one()
        
        # Final validation before creation
        self._validate_appointment_data()
        
        # Create appointment
        appointment_vals = self._prepare_appointment_values()
        appointment = self.env['support.appointment'].create(appointment_vals)
        
        _logger.info(f"Appointment {appointment.name} created via wizard by {self.env.user.name}")
        
        # Return action to view the created appointment
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointment Created'),
            'res_model': 'support.appointment',
            'res_id': appointment.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_customer_id': appointment.customer_id.id,
                'default_technician_id': appointment.technician_id.id,
            }
        }

    def action_create_and_continue(self):
        """Create appointment and return to wizard for creating another"""
        self.ensure_one()
        
        # Create the appointment
        self.action_create_appointment()
        
        # Return new wizard with some fields pre-filled
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Another Appointment'),
            'res_model': 'support.appointment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_technician_id': self.technician_id.id,
                'default_duration': self.duration,
                'default_priority': self.priority,
                'default_send_confirmation_email': self.send_confirmation_email,
                'default_send_reminder_email': self.send_reminder_email,
            }
        }

    def _validate_appointment_data(self):
        """Perform final validation before creating appointment"""
        # Check for conflicts one more time
        if self.conflicts_found:
            raise ValidationError(_(
                'Cannot create appointment due to scheduling conflicts:\n%s'
            ) % self.conflict_message)
        
        # Validate past date
        if self.scheduled_date <= fields.Datetime.now():
            raise ValidationError(_('Cannot schedule appointments in the past.'))
        
        # Validate technician permissions
        if not self.technician_id.has_group('support_center.group_support_technician'):
            raise ValidationError(_(
                'The selected user is not a support technician. '
                'Please assign the user to the Support Technician group first.'
            ))
        
        # Validate duration
        if self.duration <= 0:
            raise ValidationError(_('Appointment duration must be greater than 0.'))

    def _prepare_appointment_values(self):
        """Prepare values for appointment creation"""
        values = {
            'customer_id': self.customer_id.id,
            'technician_id': self.technician_id.id,
            'scheduled_date': self.scheduled_date,
            'duration': self.duration,
            'priority': self.priority,
            'description': self.description or '',
            'location': self.location or '',
            'send_confirmation_email': self.send_confirmation_email,
            'send_reminder_email': self.send_reminder_email,
            'status': 'draft',
            'created_via': 'internal',
        }
        
        # Link to existing ticket if specified
        if self.existing_ticket_id:
            values['helpdesk_ticket_id'] = self.existing_ticket_id.id
        
        return values

    @api.model
    def get_available_technicians(self, date_start, date_end):
        """Get technicians available during the specified time period"""
        all_technicians = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('support_center.group_support_technician').id)
        ])
        
        # Find technicians with conflicts
        busy_technicians = self.env['support.appointment'].search([
            ('scheduled_date', '<', date_end),
            ('end_datetime', '>', date_start),
            ('status', 'in', ['confirmed', 'in_progress'])
        ]).mapped('technician_id')
        
        # Return available technicians
        return all_technicians - busy_technicians

    def action_suggest_times(self):
        """Suggest alternative appointment times"""
        self.ensure_one()
        
        if not self.technician_id or not self.duration:
            raise UserError(_('Please select a technician and duration first.'))
        
        suggestions = self._find_available_slots()
        
        if not suggestions:
            raise UserError(_('No available slots found for the next 7 days.'))
        
        # Return wizard with suggested times
        return {
            'type': 'ir.actions.act_window',
            'name': _('Suggested Appointment Times'),
            'res_model': 'support.appointment.suggestions',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_suggestions': suggestions,
                'default_wizard_id': self.id,
            }
        }

    def _find_available_slots(self):
        """Find available time slots for the technician"""
        slots = []
        start_date = fields.Datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        for day_offset in range(7):  # Check next 7 days
            check_date = start_date + timedelta(days=day_offset)
            
            # Skip weekends (basic implementation)
            if check_date.weekday() >= 5:
                continue
                
            # Check hourly slots from 8 AM to 5 PM
            for hour in range(8, 17):
                slot_start = check_date.replace(hour=hour)
                slot_end = slot_start + timedelta(hours=self.duration)
                
                # Check if slot is available
                conflicts = self.env['support.appointment'].search_count([
                    ('technician_id', '=', self.technician_id.id),
                    ('scheduled_date', '<', slot_end),
                    ('end_datetime', '>', slot_start),
                    ('status', 'in', ['confirmed', 'in_progress'])
                ])
                
                if not conflicts:
                    slots.append({
                        'datetime': slot_start,
                        'display_name': slot_start.strftime('%A, %B %d at %I:%M %p')
                    })
                    
                    if len(slots) >= 5:  # Limit to 5 suggestions
                        break
            
            if len(slots) >= 5:
                break
        
        return slots
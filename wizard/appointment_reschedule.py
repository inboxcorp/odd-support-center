# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class AppointmentReschedule(models.TransientModel):
    _name = 'support.appointment.reschedule'
    _description = 'Reschedule Appointment Wizard'

    appointment_id = fields.Many2one(
        'support.appointment',
        string='Appointment',
        required=True,
        readonly=True
    )
    
    # Current appointment details (readonly)
    current_customer = fields.Char(
        string='Customer',
        related='appointment_id.customer_id.name',
        readonly=True
    )
    current_date = fields.Datetime(
        string='Current Date & Time',
        readonly=True
    )
    current_technician = fields.Many2one(
        'res.users',
        string='Current Technician',
        readonly=True
    )
    current_status = fields.Selection(
        related='appointment_id.status',
        readonly=True
    )
    
    # New appointment details
    new_date = fields.Datetime(
        string='New Date & Time',
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(hours=1)
    )
    new_technician_id = fields.Many2one(
        'res.users',
        string='New Technician',
        domain=[('groups_id', 'in', 'support_center.group_support_technician')],
        help="Leave empty to keep current technician"
    )
    duration = fields.Float(
        string='Duration (Hours)',
        related='appointment_id.duration',
        readonly=True
    )
    
    # Reschedule options
    reason = fields.Text(
        string='Reason for Reschedule',
        help="Explain why the appointment is being rescheduled"
    )
    notify_customer = fields.Boolean(
        string='Notify Customer',
        default=True,
        help="Send email notification to customer about the change"
    )
    notify_technician = fields.Boolean(
        string='Notify New Technician',
        default=True,
        help="Send notification to the new technician (if changed)"
    )
    
    # Conflict detection
    conflicts_found = fields.Boolean(
        string='Conflicts Found',
        default=False,
        readonly=True
    )
    conflict_details = fields.Text(
        string='Conflict Details',
        readonly=True
    )

    @api.onchange('new_date', 'new_technician_id')
    def _onchange_check_conflicts(self):
        """Check for conflicts when date or technician changes"""
        if self.new_date and self.duration:
            self._check_reschedule_conflicts()

    def _check_reschedule_conflicts(self):
        """Check for scheduling conflicts with the new time/technician"""
        self.conflicts_found = False
        self.conflict_details = False
        
        # Determine which technician to check
        check_technician = self.new_technician_id or self.current_technician
        if not check_technician:
            return
            
        end_datetime = self.new_date + timedelta(hours=self.duration)
        
        # Search for conflicting appointments
        conflicts = self.env['support.appointment'].search([
            ('technician_id', '=', check_technician.id),
            ('scheduled_date', '<', end_datetime),
            ('end_datetime', '>', self.new_date),
            ('status', 'in', ['confirmed', 'in_progress']),
            ('id', '!=', self.appointment_id.id)  # Exclude current appointment
        ])
        
        if conflicts:
            self.conflicts_found = True
            conflict_list = []
            for conflict in conflicts:
                conflict_list.append(
                    f"• {conflict.name}: {conflict.scheduled_date.strftime('%Y-%m-%d %H:%M')} - "
                    f"{conflict.end_datetime.strftime('%H:%M')} ({conflict.customer_id.name})"
                )
            
            self.conflict_details = "Conflicts found:\n" + "\n".join(conflict_list)

    @api.onchange('new_date')
    def _onchange_validate_new_date(self):
        """Validate the new appointment date"""
        if self.new_date:
            # Check if date is in the past
            if self.new_date <= fields.Datetime.now():
                return {
                    'warning': {
                        'title': _('Invalid Date'),
                        'message': _('Cannot reschedule to a past date. Please select a future date and time.')
                    }
                }
            
            # Check if it's the same as current date
            if self.new_date == self.current_date and not self.new_technician_id:
                return {
                    'warning': {
                        'title': _('No Changes'),
                        'message': _('The selected date and time is the same as current. Please select a different time or technician.')
                    }
                }

    def action_reschedule(self):
        """Execute the reschedule operation"""
        self.ensure_one()
        
        # Validate before rescheduling
        self._validate_reschedule()
        
        # Prepare update values
        update_vals = {
            'scheduled_date': self.new_date,
        }
        
        # Update technician if changed
        if self.new_technician_id:
            update_vals['technician_id'] = self.new_technician_id.id
        
        # Update the appointment
        self.appointment_id.write(update_vals)
        
        # Log the reschedule reason
        if self.reason:
            self.appointment_id.message_post(
                body=f"Appointment rescheduled. Reason: {self.reason}",
                message_type='comment'
            )
        
        # Send notifications
        self._send_reschedule_notifications()
        
        # Return to appointment form
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointment Rescheduled'),
            'res_model': 'support.appointment',
            'res_id': self.appointment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_suggest_alternatives(self):
        """Suggest alternative times for rescheduling"""
        self.ensure_one()
        
        technician = self.new_technician_id or self.current_technician
        if not technician:
            raise UserError(_('Please select a technician first.'))
        
        # Find available slots
        suggestions = self._find_alternative_slots(technician)
        
        if not suggestions:
            raise UserError(_('No alternative slots found for the next 7 days.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Alternative Times'),
            'res_model': 'support.appointment.reschedule.suggestions',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_suggestions': suggestions,
                'default_reschedule_wizard_id': self.id,
            }
        }

    def _validate_reschedule(self):
        """Validate reschedule request"""
        # Check for conflicts
        if self.conflicts_found:
            raise ValidationError(_(
                'Cannot reschedule due to conflicts:\n%s'
            ) % self.conflict_details)
        
        # Check date validity
        if self.new_date <= fields.Datetime.now():
            raise ValidationError(_('Cannot reschedule to a past date.'))
        
        # Check if appointment can be rescheduled
        if self.appointment_id.status == 'completed':
            raise ValidationError(_('Cannot reschedule a completed appointment.'))
        
        if self.appointment_id.status == 'cancelled':
            raise ValidationError(_('Cannot reschedule a cancelled appointment.'))
        
        # Check permissions
        if not self.appointment_id.can_edit():
            raise ValidationError(_('You do not have permission to reschedule this appointment.'))

    def _send_reschedule_notifications(self):
        """Send notifications about the reschedule"""
        appointment = self.appointment_id
        
        # Notify customer if requested
        if self.notify_customer and appointment.customer_id.email:
            template = self.env.ref('support_center.email_template_appointment_reschedule', raise_if_not_found=False)
            if template:
                template.with_context(reschedule_reason=self.reason).send_mail(appointment.id, force_send=True)
        
        # Notify new technician if changed
        if self.notify_technician and self.new_technician_id and self.new_technician_id != self.current_technician:
            appointment.message_post(
                body=f"You have been assigned to rescheduled appointment {appointment.name}",
                partner_ids=[self.new_technician_id.partner_id.id],
                message_type='notification'
            )

    def _find_alternative_slots(self, technician):
        """Find alternative available time slots"""
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
                
                # Skip the current appointment time
                if (slot_start == self.current_date.replace(minute=0, second=0, microsecond=0)):
                    continue
                
                # Check if slot is available
                conflicts = self.env['support.appointment'].search_count([
                    ('technician_id', '=', technician.id),
                    ('scheduled_date', '<', slot_end),
                    ('end_datetime', '>', slot_start),
                    ('status', 'in', ['confirmed', 'in_progress']),
                    ('id', '!=', self.appointment_id.id)
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
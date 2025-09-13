# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SupportAppointment(models.Model):
    _name = 'support.appointment'
    _description = 'Support Center Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc'

    # Core fields
    name = fields.Char(
        string='Reference', 
        required=True, 
        copy=False, 
        readonly=True, 
        default='New',
        tracking=True
    )
    customer_id = fields.Many2one(
        'res.partner', 
        string='Customer', 
        required=True, 
        tracking=True
    )
    technician_id = fields.Many2one(
        'res.users', 
        string='Technician', 
        required=True, 
        tracking=True,
        domain=[('groups_id', 'in', 'support_center.group_support_technician')]
    )
    scheduled_date = fields.Datetime(
        string='Scheduled Date', 
        required=True, 
        tracking=True
    )
    duration = fields.Float(
        string='Duration (Hours)', 
        default=1.0,
        help="Estimated duration in hours"
    )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True, string='Status')
    
    description = fields.Text(
        string='Description',
        help="Appointment notes and service details"
    )
    location = fields.Char(
        string='Location',
        help="Service location or address"
    )
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='normal', string='Priority')
    
    created_via = fields.Selection([
        ('internal', 'Internal'),
        ('api', 'External API'),
        ('automation', 'Automation')
    ], default='internal', string='Created Via')
    
    # Integration fields
    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket', 
        string='Related Ticket', 
        required=True,
        help="Every appointment must be linked to a helpdesk ticket"
    )
    
    # Email notification fields
    send_confirmation_email = fields.Boolean(
        string='Send Confirmation Email', 
        default=False,
        help="Send confirmation email to customer when appointment is created"
    )
    send_reminder_email = fields.Boolean(
        string='Send Reminder Email', 
        default=False,
        help="Send reminder email 24 hours before appointment"
    )
    confirmation_sent = fields.Boolean(
        string='Confirmation Sent', 
        default=False,
        readonly=True
    )
    reminder_sent = fields.Boolean(
        string='Reminder Sent', 
        default=False,
        readonly=True
    )

    # Computed fields
    end_datetime = fields.Datetime(
        string='End Time',
        compute='_compute_end_datetime',
        store=True
    )
    
    # Archive field for cleanup
    active = fields.Boolean(default=True, help="Uncheck to archive this appointment")

    @api.depends('scheduled_date', 'duration')
    def _compute_end_datetime(self):
        """Compute end datetime based on start time and duration"""
        for record in self:
            if record.scheduled_date and record.duration:
                record.end_datetime = record.scheduled_date + timedelta(hours=record.duration)
            else:
                record.end_datetime = False

    @api.model
    def create(self, vals):
        """Override create to auto-generate sequence and create ticket"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('support.appointment') or 'New'
        
        # Auto-create helpdesk ticket if not provided
        if not vals.get('helpdesk_ticket_id'):
            ticket_vals = {
                'name': f"Support Appointment: {vals.get('name', 'New')}",
                'partner_id': vals.get('customer_id'),
                'user_id': vals.get('technician_id'),
                'description': vals.get('description', ''),
            }
            ticket = self.env['helpdesk.ticket'].create(ticket_vals)
            vals['helpdesk_ticket_id'] = ticket.id
            _logger.info(f"Auto-created helpdesk ticket {ticket.id} for appointment")
            
        appointment = super().create(vals)
        
        # Send confirmation email if enabled
        if appointment.send_confirmation_email:
            appointment._send_confirmation_email()
            
        _logger.info(f"Appointment {appointment.name} created successfully")
        return appointment

    def write(self, vals):
        """Override write to track changes and handle validations"""
        # Store old values for comparison
        old_values = {}
        for record in self:
            old_values[record.id] = {
                'status': record.status,
                'technician_id': record.technician_id.id if record.technician_id else False,
                'scheduled_date': record.scheduled_date,
                'duration': record.duration,
                'customer_id': record.customer_id.id if record.customer_id else False,
            }
        
        result = super().write(vals)
        
        # Process changes for each record
        for record in self:
            old_data = old_values[record.id]
            record._process_appointment_changes(old_data, vals)
            
        return result

    def _process_appointment_changes(self, old_values, new_vals):
        """Process and log appointment changes"""
        self.ensure_one()
        changes = []
        
        # Track status changes
        if 'status' in new_vals and new_vals['status'] != old_values['status']:
            old_status_display = dict(self._fields['status'].selection)[old_values['status']]
            new_status_display = dict(self._fields['status'].selection)[self.status]
            changes.append(f"Status: {old_status_display} → {new_status_display}")
            
            # Update related helpdesk ticket status
            self._update_ticket_status()
            
            _logger.info(f"Appointment {self.name} status changed: {old_values['status']} → {self.status}")
        
        # Track technician changes
        if 'technician_id' in new_vals and new_vals['technician_id'] != old_values['technician_id']:
            old_tech_name = self.env['res.users'].browse(old_values['technician_id']).name if old_values['technician_id'] else 'None'
            new_tech_name = self.technician_id.name
            changes.append(f"Technician: {old_tech_name} → {new_tech_name}")
        
        # Track scheduling changes
        if 'scheduled_date' in new_vals and new_vals['scheduled_date'] != old_values['scheduled_date']:
            old_date_str = old_values['scheduled_date'].strftime('%Y-%m-%d %H:%M') if old_values['scheduled_date'] else 'None'
            new_date_str = self.scheduled_date.strftime('%Y-%m-%d %H:%M')
            changes.append(f"Scheduled Date: {old_date_str} → {new_date_str}")
        
        # Track duration changes
        if 'duration' in new_vals and new_vals['duration'] != old_values['duration']:
            changes.append(f"Duration: {old_values['duration']}h → {self.duration}h")
        
        # Track customer changes
        if 'customer_id' in new_vals and new_vals['customer_id'] != old_values['customer_id']:
            old_customer_name = self.env['res.partner'].browse(old_values['customer_id']).name if old_values['customer_id'] else 'None'
            new_customer_name = self.customer_id.name
            changes.append(f"Customer: {old_customer_name} → {new_customer_name}")
        
        # Log changes to the chatter
        if changes:
            change_message = "Appointment updated:\n• " + "\n• ".join(changes)
            self.message_post(body=change_message, message_type='comment')
        
        # Send notifications for critical changes
        if 'scheduled_date' in new_vals or 'technician_id' in new_vals:
            self._notify_appointment_changes()

    def _notify_appointment_changes(self):
        """Send notifications when critical appointment details change"""
        # Send notification to assigned technician
        if self.technician_id:
            self.message_post(
                body=f"You have been assigned to appointment {self.name}",
                partner_ids=[self.technician_id.partner_id.id],
                message_type='notification'
            )
        
        # Optional: Send email to customer about changes (if enabled)
        if self.send_confirmation_email and self.status in ['confirmed', 'in_progress']:
            template = self.env.ref('support_center.email_template_appointment_update', raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)

    @api.constrains('scheduled_date', 'technician_id', 'duration')
    def _check_appointment_validity(self):
        """Validate appointment constraints"""
        for record in self:
            # Past date validation
            if record.scheduled_date <= fields.Datetime.now():
                raise ValidationError(_("Cannot schedule appointments in the past."))
            
            # Technician availability validation
            conflicts = self.search([
                ('technician_id', '=', record.technician_id.id),
                ('scheduled_date', '<', record.end_datetime),
                ('end_datetime', '>', record.scheduled_date),
                ('status', 'in', ['confirmed', 'in_progress']),
                ('id', '!=', record.id)
            ])
            if conflicts:
                conflict_times = ', '.join([
                    f"{c.scheduled_date.strftime('%Y-%m-%d %H:%M')} - {c.end_datetime.strftime('%H:%M')}"
                    for c in conflicts
                ])
                raise ValidationError(_(
                    "Technician %s has conflicting appointments at this time:\n%s"
                ) % (record.technician_id.name, conflict_times))

    @api.constrains('technician_id')
    def _check_technician_group(self):
        """Ensure assigned user is a support technician"""
        for record in self:
            if record.technician_id and not record.technician_id.has_group('support_center.group_support_technician'):
                raise ValidationError(_(
                    "User %s must be a member of the Support Technician group"
                ) % record.technician_id.name)

    def action_confirm(self):
        """Confirm appointment and update ticket status"""
        self.ensure_one()
        self.status = 'confirmed'
        self._update_ticket_status()
        self.message_post(body=_("Appointment confirmed"))
        
    def action_start(self):
        """Start appointment work"""
        self.ensure_one()
        self.status = 'in_progress'
        self._update_ticket_status()
        self.message_post(body=_("Appointment started"))
        
    def action_complete(self):
        """Complete appointment and close ticket"""
        self.ensure_one()
        self.status = 'completed'
        self._update_ticket_status()
        self.message_post(body=_("Appointment completed"))
        
    def action_cancel(self):
        """Open cancel appointment wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Appointment'),
            'res_model': 'support.appointment.cancel',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_appointment_id': self.id,
            }
        }
    
    def action_cancel_direct(self):
        """Direct cancellation without wizard (for simple cases)"""
        self.ensure_one()
        self.status = 'cancelled'
        self._update_ticket_status()
        self.message_post(body=_("Appointment cancelled"))
        
    def action_reschedule(self):
        """Open wizard to reschedule appointment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule Appointment'),
            'res_model': 'support.appointment.reschedule',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_appointment_id': self.id,
                'default_current_date': self.scheduled_date,
                'default_current_technician': self.technician_id.id,
                'default_duration': self.duration,
            }
        }
    
    def can_edit(self):
        """Check if current user can edit this appointment"""
        self.ensure_one()
        # Managers can edit all appointments
        if self.env.user.has_group('support_center.group_support_manager'):
            return True
        # Technicians can only edit their own appointments
        if self.technician_id == self.env.user:
            return True
        return False
    
    def can_edit_field(self, field_name):
        """Check if specific field can be edited based on status and user"""
        self.ensure_one()
        
        # Basic edit permission check
        if not self.can_edit():
            return False
            
        # Status-based field restrictions
        status_restrictions = {
            'completed': ['status'],  # Only status can be changed
            'cancelled': [],  # Nothing can be changed
        }
        
        restricted_fields = status_restrictions.get(self.status, [])
        if field_name in restricted_fields and field_name != 'status':
            return False
            
        # Date restrictions - cannot edit past appointments unless manager
        if field_name in ['scheduled_date', 'technician_id'] and self.scheduled_date <= fields.Datetime.now():
            return self.env.user.has_group('support_center.group_support_manager')
            
        return True
    
    @api.model
    def get_edit_warnings(self, appointment_id, vals):
        """Get warnings about editing this appointment"""
        appointment = self.browse(appointment_id)
        warnings = []
        
        # Check if appointment is in the past
        if appointment.scheduled_date <= fields.Datetime.now():
            warnings.append(_("This appointment is in the past. Editing may affect historical records."))
        
        # Check if appointment is in progress
        if appointment.status == 'in_progress':
            warnings.append(_("This appointment is currently in progress. Changes may affect ongoing work."))
        
        # Check for scheduling conflicts if changing date/technician
        if 'scheduled_date' in vals or 'technician_id' in vals:
            new_technician = vals.get('technician_id', appointment.technician_id.id)
            new_date = vals.get('scheduled_date', appointment.scheduled_date)
            new_duration = vals.get('duration', appointment.duration)
            
            end_datetime = new_date + timedelta(hours=new_duration)
            
            conflicts = self.search([
                ('technician_id', '=', new_technician),
                ('scheduled_date', '<', end_datetime),
                ('end_datetime', '>', new_date),
                ('status', 'in', ['confirmed', 'in_progress']),
                ('id', '!=', appointment_id)
            ])
            
            if conflicts:
                conflict_names = ', '.join(conflicts.mapped('name'))
                warnings.append(_(
                    "Scheduling conflict detected with appointments: %s"
                ) % conflict_names)
        
        return warnings

    def _update_ticket_status(self):
        """Update related helpdesk ticket status based on appointment status"""
        if not self.helpdesk_ticket_id:
            return
            
        ticket = self.helpdesk_ticket_id
        status_mapping = {
            'draft': 'new',
            'confirmed': 'in_progress', 
            'in_progress': 'in_progress',
            'completed': 'solved',
            'cancelled': 'cancelled'
        }
        
        # Try to find the appropriate stage
        stage_domain = [('name', 'ilike', status_mapping.get(self.status, 'new'))]
        stages = self.env['helpdesk.stage'].search(stage_domain, limit=1)
        
        if stages:
            ticket.stage_id = stages[0]

    def _send_confirmation_email(self):
        """Send confirmation email using Odoo's mail system"""
        if not self.confirmation_sent:
            template = self.env.ref('support_center.email_template_appointment_confirmation', raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)
                self.confirmation_sent = True
                _logger.info(f"Confirmation email sent for appointment {self.name}")

    @api.model
    def get_calendar_data(self, domain=None, fields=None):
        """Get appointments for calendar view with proper security"""
        if not domain:
            domain = []
            
        # Apply security: technicians see only their appointments
        if not self.env.user.has_group('support_center.group_support_manager'):
            domain.append(('technician_id', '=', self.env.user.id))
            
        if not fields:
            fields = [
                'name', 'customer_id', 'technician_id', 
                'scheduled_date', 'end_datetime', 'status', 'priority'
            ]
            
        return self.search_read(domain, fields)

    @api.model
    def check_upcoming_reminders(self):
        """Cron job method to send 24-hour reminder emails"""
        tomorrow = fields.Datetime.now() + timedelta(hours=24)
        start_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        upcoming_appointments = self.search([
            ('scheduled_date', '>=', start_time),
            ('scheduled_date', '<', end_time),
            ('status', 'in', ['confirmed', 'in_progress']),
            ('send_reminder_email', '=', True),
            ('reminder_sent', '=', False)
        ])
        
        for appointment in upcoming_appointments:
            appointment._send_reminder_email()

    def _send_reminder_email(self):
        """Send 24-hour reminder email"""
        template = self.env.ref('support_center.email_template_appointment_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.reminder_sent = True
            _logger.info(f"Reminder email sent for appointment {self.name}")

    @api.model
    def cleanup_old_appointments(self):
        """Optional cleanup method for old cancelled appointments (older than 6 months)"""
        cutoff_date = fields.Datetime.now() - timedelta(days=180)
        old_cancelled = self.search([
            ('status', '=', 'cancelled'),
            ('scheduled_date', '<', cutoff_date)
        ])
        
        if old_cancelled:
            _logger.info(f"Cleaning up {len(old_cancelled)} old cancelled appointments")
            # Archive instead of delete to preserve data integrity
            old_cancelled.write({'active': False})
        
        return len(old_cancelled)

    @api.model
    def generate_weekly_stats(self):
        """Optional method to generate weekly appointment statistics"""
        week_start = fields.Datetime.now() - timedelta(days=7)
        week_end = fields.Datetime.now()
        
        appointments_this_week = self.search([
            ('scheduled_date', '>=', week_start),
            ('scheduled_date', '<=', week_end)
        ])
        
        stats = {
            'total': len(appointments_this_week),
            'completed': len(appointments_this_week.filtered(lambda a: a.status == 'completed')),
            'cancelled': len(appointments_this_week.filtered(lambda a: a.status == 'cancelled')),
            'in_progress': len(appointments_this_week.filtered(lambda a: a.status == 'in_progress')),
        }
        
        _logger.info(f"Weekly appointment stats: {stats}")
        
        # Optional: Could send this to managers via email or create a report
        # For now, just log the statistics
        return stats
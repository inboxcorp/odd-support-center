# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AppointmentCancel(models.TransientModel):
    _name = 'support.appointment.cancel'
    _description = 'Cancel Appointment Wizard'

    appointment_id = fields.Many2one(
        'support.appointment',
        string='Appointment',
        required=True,
        readonly=True
    )
    
    # Appointment details (readonly)
    customer_name = fields.Char(
        string='Customer',
        related='appointment_id.customer_id.name',
        readonly=True
    )
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
        related='appointment_id.scheduled_date',
        readonly=True
    )
    technician_name = fields.Char(
        string='Technician',
        related='appointment_id.technician_id.name',
        readonly=True
    )
    current_status = fields.Selection(
        related='appointment_id.status',
        readonly=True
    )
    
    # Cancellation details
    reason = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('customer_unavailable', 'Customer Not Available'),
        ('technician_unavailable', 'Technician Not Available'),
        ('emergency', 'Emergency'),
        ('equipment_issue', 'Equipment/Technical Issue'),
        ('weather', 'Weather Conditions'),
        ('rescheduled', 'Rescheduled to Different Time'),
        ('duplicate', 'Duplicate Appointment'),
        ('other', 'Other')
    ], string='Cancellation Reason', required=True)
    
    reason_details = fields.Text(
        string='Additional Details',
        help="Provide additional context about the cancellation"
    )
    
    # Notification options
    notify_customer = fields.Boolean(
        string='Notify Customer',
        default=True,
        help="Send cancellation email to customer"
    )
    notify_technician = fields.Boolean(
        string='Notify Technician',
        default=True,
        help="Send notification to technician"
    )
    
    # Refund/billing options (if applicable)
    refund_required = fields.Boolean(
        string='Refund Required',
        default=False,
        help="Mark if customer refund is required"
    )
    refund_notes = fields.Text(
        string='Refund Notes',
        help="Notes about refund processing"
    )

    @api.onchange('reason')
    def _onchange_reason_defaults(self):
        """Set default notification preferences based on reason"""
        if self.reason == 'customer_request':
            self.notify_customer = False  # Customer already knows
            self.notify_technician = True
            self.refund_required = True
        elif self.reason == 'technician_unavailable':
            self.notify_customer = True
            self.notify_technician = False  # Technician already knows
            self.refund_required = False
        elif self.reason == 'rescheduled':
            self.notify_customer = False  # Will be notified via reschedule
            self.notify_technician = False
            self.refund_required = False
        else:
            self.notify_customer = True
            self.notify_technician = True
            self.refund_required = False

    def action_cancel_appointment(self):
        """Execute the cancellation"""
        self.ensure_one()
        
        # Validate cancellation
        self._validate_cancellation()
        
        # Update appointment status
        self.appointment_id.write({
            'status': 'cancelled'
        })
        
        # Log cancellation details
        self._log_cancellation()
        
        # Send notifications
        self._send_cancellation_notifications()
        
        # Handle refund if required
        if self.refund_required:
            self._process_refund()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointment Cancelled'),
            'res_model': 'support.appointment',
            'res_id': self.appointment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel_and_reschedule(self):
        """Cancel this appointment and open reschedule wizard"""
        self.ensure_one()
        
        # First cancel the appointment
        self.action_cancel_appointment()
        
        # Then open create wizard for new appointment
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Replacement Appointment'),
            'res_model': 'support.appointment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_id': self.appointment_id.customer_id.id,
                'default_technician_id': self.appointment_id.technician_id.id,
                'default_duration': self.appointment_id.duration,
                'default_priority': self.appointment_id.priority,
                'default_location': self.appointment_id.location,
                'default_description': f"Replacement for cancelled appointment {self.appointment_id.name}",
            }
        }

    def _validate_cancellation(self):
        """Validate that appointment can be cancelled"""
        appointment = self.appointment_id
        
        # Check if already cancelled
        if appointment.status == 'cancelled':
            raise ValidationError(_('This appointment is already cancelled.'))
        
        # Check if completed
        if appointment.status == 'completed':
            raise ValidationError(_('Cannot cancel a completed appointment.'))
        
        # Check permissions
        if not appointment.can_edit():
            raise ValidationError(_('You do not have permission to cancel this appointment.'))
        
        # Warn about cancelling in-progress appointments
        if appointment.status == 'in_progress':
            raise UserError(_(
                'This appointment is currently in progress. '
                'Please contact the technician before cancelling.'
            ))

    def _log_cancellation(self):
        """Log cancellation details to appointment chatter"""
        appointment = self.appointment_id
        
        reason_display = dict(self._fields['reason'].selection)[self.reason]
        
        cancellation_message = f"Appointment cancelled.\n\nReason: {reason_display}"
        
        if self.reason_details:
            cancellation_message += f"\nDetails: {self.reason_details}"
        
        if self.refund_required:
            cancellation_message += "\nRefund Required: Yes"
            if self.refund_notes:
                cancellation_message += f"\nRefund Notes: {self.refund_notes}"
        
        appointment.message_post(
            body=cancellation_message,
            message_type='comment'
        )

    def _send_cancellation_notifications(self):
        """Send cancellation notifications"""
        appointment = self.appointment_id
        
        # Notify customer
        if self.notify_customer and appointment.customer_id.email:
            template = self.env.ref('support_center.email_template_appointment_cancellation', raise_if_not_found=False)
            if template:
                ctx = {
                    'cancellation_reason': dict(self._fields['reason'].selection)[self.reason],
                    'cancellation_details': self.reason_details,
                    'refund_required': self.refund_required
                }
                template.with_context(**ctx).send_mail(appointment.id, force_send=True)
        
        # Notify technician
        if self.notify_technician and appointment.technician_id:
            appointment.message_post(
                body=f"Appointment {appointment.name} has been cancelled. Reason: {dict(self._fields['reason'].selection)[self.reason]}",
                partner_ids=[appointment.technician_id.partner_id.id],
                message_type='notification'
            )

    def _process_refund(self):
        """Process refund requirements (placeholder for integration with billing)"""
        # This method can be extended to integrate with billing systems
        # For now, just log the refund requirement
        appointment = self.appointment_id
        
        refund_message = f"Refund processing required for cancelled appointment {appointment.name}"
        if self.refund_notes:
            refund_message += f"\nNotes: {self.refund_notes}"
        
        # Create activity for billing team (if exists)
        billing_users = self.env['res.users'].search([('groups_id.name', 'ilike', 'billing')])
        if billing_users:
            appointment.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Process refund for cancelled appointment',
                note=refund_message,
                user_id=billing_users[0].id
            )

    @api.model
    def get_cancellation_stats(self, date_from=None, date_to=None):
        """Get cancellation statistics for reporting"""
        domain = [('status', '=', 'cancelled')]
        
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        cancelled_appointments = self.env['support.appointment'].search(domain)
        
        # Extract reasons from chatter messages (simplified)
        reasons = {}
        for appointment in cancelled_appointments:
            # This is a simplified approach - in practice, you might want to 
            # store the cancellation reason directly on the appointment
            messages = appointment.message_ids.filtered(lambda m: 'cancelled' in m.body.lower())
            if messages:
                # Extract reason from the latest cancellation message
                # This is a placeholder - implement based on your message format
                reasons[appointment.id] = 'customer_request'  # Default
        
        return {
            'total_cancelled': len(cancelled_appointments),
            'cancellation_reasons': reasons,
            'appointments': cancelled_appointments.ids
        }
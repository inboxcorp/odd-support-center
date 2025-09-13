# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AppointmentSettings(models.Model):
    _name = 'support.appointment.settings'
    _description = 'Support Center Appointment Settings'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help="Name for this configuration set"
    )
    technician_id = fields.Many2one(
        'res.users',
        string='Technician',
        help="Specific technician (leave empty for global settings)",
        domain=[('groups_id', 'in', 'support_center.group_support_technician')]
    )
    
    # Working hours configuration
    working_hours_start = fields.Float(
        string='Working Hours Start',
        default=8.0,
        help="Daily start time (24-hour format, e.g., 8.5 for 8:30 AM)"
    )
    working_hours_end = fields.Float(
        string='Working Hours End',
        default=17.0,
        help="Daily end time (24-hour format, e.g., 17.5 for 5:30 PM)"
    )
    working_days = fields.Char(
        string='Working Days',
        default='1,2,3,4,5',
        help="Comma-separated weekday numbers (1=Monday, 7=Sunday)"
    )
    
    # Appointment constraints
    max_daily_appointments = fields.Integer(
        string='Max Daily Appointments',
        default=8,
        help="Maximum number of appointments per day"
    )
    default_duration = fields.Float(
        string='Default Duration (Hours)',
        default=1.0,
        help="Default appointment duration in hours"
    )
    advance_booking_days = fields.Integer(
        string='Advance Booking Days',
        default=30,
        help="Maximum days in advance for booking"
    )
    buffer_time = fields.Float(
        string='Buffer Time (Hours)',
        default=0.5,
        help="Minimum time buffer between appointments"
    )
    
    # Email settings
    auto_confirm_emails = fields.Boolean(
        string='Auto-Send Confirmation Emails',
        default=False,
        help="Automatically send confirmation emails for new appointments"
    )
    auto_reminder_emails = fields.Boolean(
        string='Auto-Send Reminder Emails',
        default=False,
        help="Automatically send 24-hour reminder emails"
    )

    @api.constrains('working_hours_start', 'working_hours_end')
    def _check_working_hours(self):
        """Validate working hours are logical"""
        for record in self:
            if record.working_hours_start >= record.working_hours_end:
                raise ValidationError(_("Working hours end time must be after start time"))
            if record.working_hours_start < 0 or record.working_hours_start > 24:
                raise ValidationError(_("Working hours start must be between 0 and 24"))
            if record.working_hours_end < 0 or record.working_hours_end > 24:
                raise ValidationError(_("Working hours end must be between 0 and 24"))

    @api.constrains('working_days')
    def _check_working_days(self):
        """Validate working days format"""
        for record in self:
            if record.working_days:
                try:
                    days = [int(d.strip()) for d in record.working_days.split(',')]
                    if any(day < 1 or day > 7 for day in days):
                        raise ValueError()
                except (ValueError, AttributeError):
                    raise ValidationError(_("Working days must be comma-separated numbers from 1-7 (1=Monday, 7=Sunday)"))

    @api.constrains('max_daily_appointments', 'advance_booking_days')
    def _check_positive_values(self):
        """Ensure positive values for constraints"""
        for record in self:
            if record.max_daily_appointments <= 0:
                raise ValidationError(_("Maximum daily appointments must be greater than 0"))
            if record.advance_booking_days <= 0:
                raise ValidationError(_("Advance booking days must be greater than 0"))

    @api.constrains('technician_id')
    def _check_unique_technician(self):
        """Ensure only one configuration per technician"""
        for record in self:
            if record.technician_id:
                existing = self.search([
                    ('technician_id', '=', record.technician_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_(
                        "Configuration already exists for technician %s"
                    ) % record.technician_id.name)

    @api.model
    def get_settings_for_technician(self, technician_id):
        """Get settings for a specific technician, fallback to global"""
        # First try to find technician-specific settings
        technician_settings = self.search([
            ('technician_id', '=', technician_id)
        ], limit=1)
        
        if technician_settings:
            return technician_settings
            
        # Fallback to global settings (no technician specified)
        global_settings = self.search([
            ('technician_id', '=', False)
        ], limit=1)
        
        if global_settings:
            return global_settings
            
        # Create default global settings if none exist
        return self.create({
            'name': 'Default Global Settings',
            'working_hours_start': 8.0,
            'working_hours_end': 17.0,
            'working_days': '1,2,3,4,5',
            'max_daily_appointments': 8,
            'default_duration': 1.0,
            'advance_booking_days': 30,
            'buffer_time': 0.5,
        })

    def get_working_days_list(self):
        """Convert working days string to list of integers"""
        self.ensure_one()
        if not self.working_days:
            return [1, 2, 3, 4, 5]  # Default to weekdays
        return [int(d.strip()) for d in self.working_days.split(',')]

    def is_working_day(self, date):
        """Check if given date is a working day"""
        self.ensure_one()
        weekday = date.isoweekday()  # 1=Monday, 7=Sunday
        return weekday in self.get_working_days_list()

    def is_working_hour(self, time_float):
        """Check if given time (float hours) is within working hours"""
        self.ensure_one()
        return self.working_hours_start <= time_float <= self.working_hours_end
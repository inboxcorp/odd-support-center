# Support Center Automation Guide

## Overview

The Support Center module includes comprehensive automation capabilities using Odoo's built-in automation framework instead of custom REST APIs. This approach provides better security, maintainability, and integration with the existing Odoo ecosystem.

## Automation Features

### 1. Email Reminder System

**Cron Job: Send Appointment Reminders**
- **Schedule**: Runs every hour
- **Purpose**: Sends 24-hour reminder emails to customers
- **Configuration**: Located in `data/cron_jobs.xml`
- **Status**: Active by default

**How it works:**
- Scans for appointments scheduled 24 hours from now
- Sends reminder emails to customers who have `send_reminder_email = True`
- Marks reminders as sent to prevent duplicates

### 2. External Appointment Creation

**Server Actions Available:**

#### a) Generic External Data Processing
- **Action**: `server_action_create_appointment_external`
- **Use Case**: Process structured data from external systems
- **Trigger**: Can be called via automation rules or webhooks

**Example Usage:**
```python
# External system sends data via automation context
external_data = {
    'customer_email': 'customer@example.com',
    'customer_name': 'John Doe',
    'requested_date': '2025-01-15 14:00:00',
    'description': 'Network troubleshooting needed',
    'priority': 'high',
    'location': '123 Main Street'
}

# Trigger the automation with context
env['support.appointment'].with_context(external_data=external_data).create({})
```

#### b) Email-Based Appointment Requests
- **Action**: `server_action_process_email_appointment`
- **Use Case**: Process appointment requests sent via email
- **Trigger**: Incoming email automation rules

**Setup:**
1. Configure mail alias for appointment requests
2. Set up automation rule to trigger on incoming emails
3. System automatically creates draft appointments for review

### 3. Automatic Email Notifications

**Available Automations:**

#### a) Confirmation Email Automation
- **Trigger**: When appointment status changes to 'confirmed'
- **Condition**: `send_confirmation_email = True` and `confirmation_sent = False`
- **Action**: Automatically sends confirmation email

#### b) Technician Notification
- **Trigger**: When technician is assigned or changed
- **Action**: Sends internal notification to the new technician

#### c) Ticket Status Synchronization
- **Trigger**: When appointment status changes
- **Action**: Updates related helpdesk ticket status automatically

### 4. Webhook Integration (Optional)

**Webhook Response System:**
- **Action**: `server_action_webhook_response`
- **Purpose**: Send responses back to external systems
- **Status**: Disabled by default (set `active=False`)

**Configuration:**
```bash
# Set webhook URL in system parameters
# Settings > Technical > Parameters > System Parameters
Key: support_center.webhook_response_url
Value: https://your-external-system.com/webhook/response
```

## Configuration Guide

### 1. Enable/Disable Automation Rules

Navigate to: **Settings > Technical > Automation > Automated Actions**

Available rules:
- Auto-send Confirmation Email (Active)
- Notify Technician on Assignment (Active)  
- Sync Helpdesk Ticket Status (Active)
- Webhook Appointment Creation (Inactive)

### 2. Cron Job Management

Navigate to: **Settings > Technical > Automation > Scheduled Actions**

Available jobs:
- Send Appointment Reminders (Active - every hour)
- Cleanup Old Appointments (Inactive - daily)
- Generate Appointment Statistics (Inactive - weekly)

### 3. Email Template Customization

Navigate to: **Settings > Technical > Email > Templates**

Available templates:
- Support Appointment Confirmation
- Support Appointment Reminder
- Support Appointment Rescheduled
- Support Appointment Cancelled
- Support Appointment Updated

## External System Integration Examples

### Example 1: Website Form Integration

**Step 1**: Create a mail alias `appointments@yourcompany.com`

**Step 2**: Configure your website contact form to send emails to this alias

**Step 3**: Set up automation rule to process these emails automatically

### Example 2: Third-party API Integration

**Option A: Email-based**
```python
# External system sends email with structured data
subject = "APPOINTMENT_REQUEST"
body = """
customer_email: customer@example.com
customer_name: John Doe
requested_date: 2025-01-15 14:00:00
description: Network issue
priority: high
"""
# Send email to appointments@yourcompany.com
```

**Option B: Direct automation trigger**
```python
# Call Odoo automation via XML-RPC or other integration
external_data = {...}  # appointment data
odoo.env['support.appointment'].with_context(external_data=external_data).create({})
```

## Security Considerations

### Authentication
- All automation uses Odoo's built-in security model
- No custom API keys or authentication required
- Server actions run with appropriate user permissions

### Data Validation
- All external data is validated through Odoo model constraints
- Email addresses are verified before creating contacts
- Date/time validation prevents past appointments
- Technician availability is checked automatically

### Audit Trail
- All automated actions are logged
- Email notifications are tracked
- Appointment changes trigger automatic history tracking

## Troubleshooting

### Common Issues

**1. Reminder emails not sending**
- Check cron job is active
- Verify SMTP configuration
- Ensure appointments have `send_reminder_email = True`

**2. External appointments not creating**
- Check automation rule is active
- Verify data format matches expected structure
- Review server logs for validation errors

**3. Confirmation emails not sending**
- Verify email templates exist
- Check `send_confirmation_email` flag on appointments
- Ensure automation rule for confirmations is active

### Logs and Monitoring

**Check automation logs:**
1. Go to Settings > Technical > Automation > Scheduled Actions
2. Click on the specific cron job
3. Check "Last Run" and "Next Run" times

**Check email queue:**
1. Go to Settings > Technical > Email > Emails
2. Filter by state to see sent/failed emails

**Check server logs:**
```bash
# Look for support_center automation logs
grep "support_center.automation" /var/log/odoo/odoo.log
```

## Best Practices

1. **Test automation rules in staging** before enabling in production
2. **Monitor email delivery rates** to ensure SMTP is working correctly
3. **Set up proper error handling** for external integrations
4. **Use draft status** for externally created appointments that need review
5. **Regularly review automation logs** for any issues
6. **Keep email templates updated** with current business information

## Future Enhancements

Possible automation improvements:
- SMS notification support
- Advanced scheduling AI for technician assignment
- Customer satisfaction survey automation
- Automatic rescheduling for cancellations
- Integration with calendar applications (Google Calendar, Outlook)
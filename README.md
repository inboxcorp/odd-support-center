# Support Center - Odoo Appointment Management Module

A comprehensive appointment scheduling and management system for support teams built as an Odoo 18.0 module.

## 🚀 Features

### Core Functionality
- **📅 Interactive Calendar Views** - Visual appointment scheduling with color-coded status indicators
- **👥 Role-Based Access** - Managers see all appointments, technicians see only their assignments
- **🎫 Helpdesk Integration** - Automatic ticket creation and status synchronization
- **📧 Email Automation** - Confirmation emails, 24-hour reminders, and update notifications
- **🔄 Status Workflow** - Complete appointment lifecycle from draft to completion
- **⚡ Conflict Detection** - Automatic validation to prevent double-booking

### Advanced Features
- **🤖 External Integration** - Email-based appointment requests and webhook support
- **📊 Automation Rules** - Odoo's native automation for seamless external system integration
- **🔍 Advanced Search** - Filter by technician, date, status, and priority
- **📱 Responsive Design** - Works seamlessly in Odoo's backend interface
- **🔒 Security** - Built on Odoo's proven role-based access control system

## 📋 Requirements

- **Odoo Version**: 18.0+
- **Dependencies**: 
  - `base` (core Odoo)
  - `helpdesk` (Odoo Helpdesk module)
  - `mail` (email functionality)
  - `web` (web interface)

## 🔧 Installation

### Method 1: Clone Repository
```bash
# Navigate to your Odoo addons directory
cd /path/to/odoo/addons

# Clone the repository
git clone https://github.com/YOUR_USERNAME/odoo-support-center.git support_center

# Restart Odoo server
sudo systemctl restart odoo

# Install via Odoo interface
# Apps → Update Apps List → Search "Support Center" → Install
```

### Method 2: Download and Extract
1. Download the latest release from GitHub
2. Extract to your Odoo addons directory as `support_center`
3. Restart Odoo and install via Apps menu

## ⚙️ Configuration

### Initial Setup
1. **Install Dependencies**: Ensure Helpdesk module is installed
2. **User Groups**: Assign users to Support Manager or Support Technician groups
3. **Email Configuration**: Configure SMTP settings for automated notifications
4. **Sequence Numbers**: Appointment references auto-generate (APPT-001, APPT-002, etc.)

### Email Automation
Configure automated emails in Settings:
- **Confirmation emails** when appointments are created
- **24-hour reminder emails** sent automatically via cron job
- **Update notifications** when appointment details change

### External Integration
- **Email-based requests**: Set up mail alias for appointment requests
- **Webhook integration**: Configure external system callbacks
- **Automation rules**: Customize automatic appointment processing

See [Automation Guide](README_AUTOMATION.md) for detailed configuration.

## 🎯 Usage

### For Support Managers
- **Dashboard Overview**: Calendar view showing all technician schedules
- **Appointment Creation**: Click calendar slots to create new appointments
- **Team Management**: Assign and reassign technicians to appointments
- **Status Monitoring**: Track appointment progress and completion rates

### For Technicians
- **Personal Calendar**: View only your assigned appointments
- **Status Updates**: Update appointment progress (confirmed → in progress → completed)
- **Customer Communication**: Access integrated customer contact information
- **Mobile Friendly**: Responsive design works on tablets and mobile devices

### For Customers (via Email Integration)
- **Automatic Confirmations**: Receive professional email confirmations
- **Timely Reminders**: 24-hour advance reminder emails
- **Status Updates**: Get notified of any schedule changes

## 🏗️ Architecture

### Technical Overview
- **Backend**: Python models with Odoo ORM
- **Frontend**: Odoo's Owl framework with custom calendar components
- **Database**: PostgreSQL with automatic schema management
- **Integration**: Native Odoo automation rules (no custom APIs)
- **Security**: Role-based access control with record-level permissions

### Data Models
- **`support.appointment`** - Core appointment records
- **`support.appointment.settings`** - Configuration and constraints
- **Integration with `helpdesk.ticket`** - Automatic ticket lifecycle
- **Integration with `res.partner`** - Customer contact management

## 📁 Project Structure

```
support_center/
├── __manifest__.py              # Module definition and dependencies
├── models/                      # Python business logic
│   ├── support_appointment.py   # Main appointment model
│   ├── appointment_settings.py  # Configuration model
│   └── __init__.py
├── views/                       # XML user interface definitions
│   ├── appointment_views.xml    # Calendar, list, and form views
│   ├── appointment_menus.xml    # Navigation menu structure
│   └── appointment_wizard_views.xml
├── security/                    # Access control and permissions
│   ├── security.xml             # User groups and record rules
│   └── ir.model.access.csv     # Model access rights
├── data/                        # Configuration and automation
│   ├── sequences.xml            # Appointment numbering
│   ├── email_templates.xml      # Professional email templates
│   ├── cron_jobs.xml           # Automated reminder system
│   └── automation_rules.xml    # External integration rules
├── static/                      # Web assets
│   └── src/
│       ├── css/                # Custom styling
│       └── js/                 # JavaScript enhancements
├── wizard/                      # Dialog interfaces
├── tests/                       # Unit tests (future)
└── README_AUTOMATION.md         # Automation configuration guide
```

## 🔒 Security Features

- **Role-Based Access**: Managers and technicians have appropriate permissions
- **Data Isolation**: Technicians can only access their own appointments
- **Audit Trail**: Complete history tracking of all appointment changes
- **Email Security**: Templates prevent information disclosure
- **Input Validation**: All external data is properly validated

## 🚀 Development Status

### ✅ Completed (MVP Ready)
- [x] **Epic 1**: Core Foundation & Calendar Views
- [x] **Epic 2**: Internal Appointment Management
- [x] **Epic 3**: External Booking & Email Automation

### 🔄 Future Enhancements (Phase 2)
- [ ] Mobile app integration
- [ ] Advanced reporting and analytics
- [ ] SMS notification support
- [ ] Calendar application sync (Google Calendar, Outlook)
- [ ] Customer self-service portal
- [ ] AI-powered technician scheduling
- [ ] Service time tracking and billing integration

## 🤝 Contributing

We welcome contributions! Please read our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** following Odoo development standards
4. **Add tests** for new functionality
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
6. **Push to the branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

### Development Setup
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/odoo-support-center.git
cd odoo-support-center

# Set up Odoo development environment
# See Odoo documentation for detailed setup instructions
```

## 📝 License

This project is licensed under the LGPL-3 License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Documentation**: [Wiki](../../wiki)
- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)

## 🏆 Credits

- **Product Owner**: Comprehensive PRD and feature requirements
- **Architect**: Technical architecture and system design
- **Developer**: Implementation using Odoo best practices
- **Built with**: [Odoo](https://www.odoo.com/) - The World's #1 Business App Platform

## 📊 Statistics

![GitHub last commit](https://img.shields.io/github/last-commit/YOUR_USERNAME/odoo-support-center)
![GitHub issues](https://img.shields.io/github/issues/YOUR_USERNAME/odoo-support-center)
![GitHub stars](https://img.shields.io/github/stars/YOUR_USERNAME/odoo-support-center)
![GitHub license](https://img.shields.io/github/license/YOUR_USERNAME/odoo-support-center)

---

**Ready to streamline your support team's scheduling?** Install the Support Center module today and transform your appointment management workflow! 🎯
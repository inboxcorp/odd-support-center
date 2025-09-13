/** @odoo-module **/

import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { patch } from "@web/core/utils/patch";

// Extend Calendar Renderer for Support Center customizations
patch(CalendarRenderer.prototype, "support_center.CalendarRenderer", {
    
    /**
     * Add custom CSS classes to calendar events based on appointment status
     */
    fcEventToCalendarEvent(fcEvent) {
        const calendarEvent = this._super(...arguments);
        
        if (fcEvent.extendedProps && fcEvent.extendedProps.status) {
            // Add status-based CSS class
            const statusClass = `status-${fcEvent.extendedProps.status}`;
            calendarEvent.className = calendarEvent.className || [];
            if (Array.isArray(calendarEvent.className)) {
                calendarEvent.className.push(statusClass);
            } else {
                calendarEvent.className += ` ${statusClass}`;
            }
            
            // Add priority-based CSS class
            if (fcEvent.extendedProps.priority && fcEvent.extendedProps.priority !== 'normal') {
                const priorityClass = `priority-${fcEvent.extendedProps.priority}`;
                if (Array.isArray(calendarEvent.className)) {
                    calendarEvent.className.push(priorityClass);
                } else {
                    calendarEvent.className += ` ${priorityClass}`;
                }
            }
        }
        
        return calendarEvent;
    },

    /**
     * Customize event content display
     */
    eventContent(info) {
        const event = info.event;
        const props = event.extendedProps;
        
        // Create custom event content with status and priority indicators
        const container = document.createElement('div');
        container.className = 'o_calendar_event_details';
        
        // Event title
        const title = document.createElement('strong');
        title.textContent = event.title;
        container.appendChild(title);
        
        // Customer name
        if (props.customer_id && props.customer_id[1]) {
            const customer = document.createElement('div');
            customer.textContent = props.customer_id[1];
            customer.style.fontSize = '10px';
            customer.style.opacity = '0.9';
            container.appendChild(customer);
        }
        
        // Status badge
        if (props.status) {
            const status = document.createElement('span');
            status.className = `badge badge-${props.status}`;
            status.textContent = props.status.replace('_', ' ').toUpperCase();
            container.appendChild(status);
        }
        
        return { domNodes: [container] };
    }
});

// Support Center Calendar Utilities
export const SupportCalendarUtils = {
    
    /**
     * Get color for technician (used for calendar event coloring)
     */
    getTechnicianColor(technicianId) {
        const colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ];
        return colors[technicianId % colors.length];
    },
    
    /**
     * Format appointment time display
     */
    formatAppointmentTime(datetime) {
        return new Date(datetime).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    },
    
    /**
     * Check if appointment is overdue
     */
    isOverdue(scheduledDate, status) {
        const now = new Date();
        const scheduled = new Date(scheduledDate);
        return scheduled < now && !['completed', 'cancelled'].includes(status);
    }
};
/**
 * Ticket modal components — TicketDetails, TicketTimeline, TimelineItem, TicketModal
 * Reuses existing ticket/log data; no backend changes.
 */
(function (global) {
  'use strict';

  const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(', ');

  const TimelineItem = {
    getMeta(log, ticket) {
      const action = String(log.action || '').toLowerCase();
      const newStatus = String(log.newStatus || '').toLowerCase();

      if (action.includes('created')) {
        return { tone: 'green', title: 'Ticket Created', icon: 'created' };
      }
      if (action.includes('assigned') || action.includes('assignment')) {
        return { tone: 'purple', title: 'Assigned', icon: 'assigned' };
      }
      if (action.includes('status')) {
        return { tone: 'orange', title: 'Status Changed', icon: 'status' };
      }
      if (action.includes('note')) {
        return { tone: 'blue', title: 'Note Added', icon: 'note' };
      }
      if (action.includes('attach')) {
        return { tone: 'gray', title: log.action, icon: 'attachment' };
      }
      if (action.includes('escalat')) {
        return { tone: 'red', title: log.action, icon: 'escalated' };
      }
      if (newStatus === 'resolved' || newStatus === 'closed') {
        return { tone: 'green', title: log.action, icon: 'resolved' };
      }
      return { tone: 'gray', title: log.action || 'Event', icon: 'default' };
    },

    getDescription(log) {
      const action = String(log.action || '').toLowerCase();
      if (action.includes('status') && log.oldStatus && log.newStatus) {
        return `${log.oldStatus} → ${log.newStatus}`;
      }
      return log.notes || '';
    },

    renderIcon(icon) {
      const icons = {
        created: '<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
        assigned: '<path d="M16 11V7a4 4 0 00-8 0v4M5 11h14v8H5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
        status: '<path d="M4 6h16M4 12h10M4 18h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
        resolved: '<path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
        note: '<path d="M21 15a4 4 0 01-4 4H8l-5 3V7a4 4 0 014-4h10a4 4 0 014 4z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
        attachment: '<path d="M16 8l-8 8a4 4 0 106-6l7-7a2 2 0 103 3l-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
        escalated: '<path d="M12 9v4m0 4h.01M10.3 4.3l-7.4 12.8A2 2 0 004.6 20h14.8a2 2 0 001.7-2.9L13.7 4.3a2 2 0 00-3.4 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
        default: '<circle cx="12" cy="12" r="4" fill="currentColor"/>'
      };
      return `<svg class="timeline-item__svg" viewBox="0 0 24 24" aria-hidden="true">${icons[icon] || icons.default}</svg>`;
    },

    render(log, ticket, helpers, isLast) {
      const meta = this.getMeta(log, ticket);
      const description = this.getDescription(log);
      const user = log.admin || 'System';
      const timestamp = helpers.formatTimelineDate(log.dateTime);

      return `
        <article class="timeline-item timeline-item--${meta.tone}${isLast ? ' timeline-item--last' : ''}">
          <div class="timeline-item__track" aria-hidden="true">
            <div class="timeline-item__icon">${this.renderIcon(meta.icon)}</div>
            ${isLast ? '' : '<div class="timeline-item__line"></div>'}
          </div>
          <div class="timeline-item__card">
            <h4 class="timeline-item__title">${helpers.escapeHtml(meta.title)}</h4>
            <p class="timeline-item__meta">${helpers.escapeHtml(timestamp)}</p>
            <p class="timeline-item__user">${helpers.escapeHtml(user)}</p>
            ${description ? `<p class="timeline-item__desc">${helpers.escapeHtml(description)}</p>` : ''}
          </div>
        </article>
      `;
    }
  };

  const TicketTimeline = {
    render(ticket, helpers) {
      const logs = [...(ticket.logs || [])];
      if (!logs.length) {
        return '<p class="timeline-empty">No activity recorded for this ticket yet.</p>';
      }

      return `
        <div class="ticket-timeline" role="list">
          ${logs.map((log, index) => TimelineItem.render(log, ticket, helpers, index === logs.length - 1)).join('')}
        </div>
      `;
    }
  };

  const TicketDetails = {
    infoField(label, value) {
      return `
        <div class="info-field">
          <dt>${label}</dt>
          <dd>${value}</dd>
        </div>
      `;
    },

    render(ticket, helpers, ticketStatuses) {
      const screenshot = ticket.screenshotDataUrl
        ? `<img class="issue-screenshot" src="${ticket.screenshotDataUrl}" alt="Ticket screenshot preview" />`
        : '<p class="small-note">No screenshot uploaded.</p>';

      return `
        <div class="detail-cards">
          <section class="detail-card" aria-labelledby="ticketInfoHeading">
            <h3 id="ticketInfoHeading" class="detail-card__title">Ticket Information</h3>
            <dl class="info-grid">
              ${this.infoField('Ticket Number', helpers.escapeHtml(ticket.ticketNumber))}
              ${this.infoField('Employee', helpers.escapeHtml(ticket.employeeName))}
              ${this.infoField('Department', helpers.escapeHtml(ticket.department))}
              ${this.infoField('Email', helpers.escapeHtml(ticket.contact))}
              ${this.infoField('Computer Name', helpers.escapeHtml(ticket.computerName))}
              ${this.infoField('Category', helpers.escapeHtml(ticket.category))}
              ${this.infoField('Priority', `<span class="badge priority-${helpers.slugify(ticket.priority)}">${helpers.escapeHtml(ticket.priority)}</span>`)}
              ${this.infoField('Status', `<span class="badge status-${helpers.slugify(ticket.status)}">${helpers.escapeHtml(ticket.status)}</span>`)}
            </dl>
          </section>

          <section class="detail-card" aria-labelledby="issueDetailsHeading">
            <h3 id="issueDetailsHeading" class="detail-card__title">Issue Details</h3>
            <div class="issue-description">
              <p>${helpers.escapeHtml(ticket.description)}</p>
            </div>
            <div class="issue-screenshot-wrap">${screenshot}</div>
          </section>

          <section class="detail-card" aria-labelledby="technicianActionsHeading">
            <h3 id="technicianActionsHeading" class="detail-card__title">Technician Actions</h3>
            <div class="technician-form">
              <label class="field">Assigned Technician
                <input id="detailTechnician" value="${helpers.escapeHtml(ticket.assignedTechnician || '')}" />
              </label>
              <label class="field">Status
                <select id="detailStatus">
                  ${ticketStatuses.map(status => `<option ${status === ticket.status ? 'selected' : ''}>${helpers.escapeHtml(status)}</option>`).join('')}
                </select>
              </label>
              <label class="field">Admin Notes
                <textarea id="detailNotes">${helpers.escapeHtml(ticket.adminNotes || '')}</textarea>
              </label>
              <button type="button" id="saveTicketButton">Save Changes</button>
            </div>
          </section>
        </div>
      `;
    }
  };

  const TicketModal = {
    activeTab: 'details',
    previouslyFocused: null,
    ticketId: null,
    elements: null,
    helpers: null,
    ticketStatuses: [],
    onSave: null,
    onClose: null,

    init(options) {
      this.helpers = options.helpers;
      this.ticketStatuses = options.ticketStatuses;
      this.onSave = options.onSave;
      this.onClose = options.onClose;
      this.elements = {
        root: document.getElementById('ticketModal'),
        dialog: document.getElementById('ticketModalDialog'),
        title: document.getElementById('ticketModalTitle'),
        number: document.getElementById('ticketModalNumber'),
        badges: document.getElementById('ticketModalBadges'),
        tabList: document.getElementById('ticketModalTabs'),
        panels: {
          details: document.getElementById('ticketModalPanelDetails'),
          activity: document.getElementById('ticketModalPanelActivity')
        },
        closeButton: document.getElementById('ticketModalClose'),
        backdrop: document.getElementById('ticketModalBackdrop')
      };

      this.elements.closeButton.addEventListener('click', () => this.close());
      this.elements.backdrop.addEventListener('click', () => this.close());
      this.elements.root.addEventListener('keydown', event => this.handleKeydown(event));
      this.elements.tabList.addEventListener('click', event => {
        const tab = event.target.closest('[data-tab]');
        if (tab) {
          this.setActiveTab(tab.dataset.tab);
        }
      });
      this.elements.tabList.addEventListener('keydown', event => this.handleTabKeydown(event));
    },

    open(ticketId, ticket) {
      if (!ticket) {
        this.close();
        return;
      }

      this.ticketId = ticketId;
      this.activeTab = 'details';
      this.previouslyFocused = document.activeElement;
      this.renderHeader(ticket);
      this.renderPanels(ticket);
      this.setActiveTab('details', false);
      this.elements.root.hidden = false;
      document.body.classList.add('modal-open');
      this.elements.closeButton.focus();
    },

    close() {
      if (this.elements.root.hidden) {
        return;
      }
      this.elements.root.hidden = true;
      document.body.classList.remove('modal-open');
      this.ticketId = null;
      if (typeof this.onClose === 'function') {
        this.onClose();
      }
      if (this.previouslyFocused && typeof this.previouslyFocused.focus === 'function') {
        this.previouslyFocused.focus();
      }
      this.previouslyFocused = null;
    },

    isOpen() {
      return !this.elements.root.hidden;
    },

    getOpenTicketId() {
      return this.ticketId;
    },

    refresh(ticket) {
      if (!this.isOpen() || !ticket || ticket.id !== this.ticketId) {
        return;
      }
      this.renderHeader(ticket);
      this.renderPanels(ticket);
      this.setActiveTab(this.activeTab, false);
    },

    renderHeader(ticket) {
      this.elements.number.textContent = `Ticket #${ticket.ticketNumber}`;
      this.elements.title.textContent = ticket.category || 'Support Request';
      this.elements.badges.innerHTML = `
        <span class="badge status-${this.helpers.slugify(ticket.status)}">${this.helpers.escapeHtml(ticket.status)}</span>
        <span class="badge priority-${this.helpers.slugify(ticket.priority)}">${this.helpers.escapeHtml(ticket.priority)}</span>
      `;
    },

    renderPanels(ticket) {
      this.elements.panels.details.innerHTML = TicketDetails.render(ticket, this.helpers, this.ticketStatuses);
      this.elements.panels.activity.innerHTML = TicketTimeline.render(ticket, this.helpers);

      const saveButton = document.getElementById('saveTicketButton');
      if (saveButton) {
        saveButton.addEventListener('click', () => {
          if (typeof this.onSave === 'function') {
            this.onSave(ticket.id);
          }
        });
      }
    },

    setActiveTab(tabName, focusTab = true) {
      this.activeTab = tabName;
      this.elements.tabList.querySelectorAll('[role="tab"]').forEach(tab => {
        const isActive = tab.dataset.tab === tabName;
        tab.classList.toggle('active', isActive);
        tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
        tab.tabIndex = isActive ? 0 : -1;
      });

      Object.entries(this.elements.panels).forEach(([name, panel]) => {
        const isActive = name === tabName;
        panel.hidden = !isActive;
        panel.classList.toggle('active', isActive);
      });

      if (focusTab) {
        const activeTab = this.elements.tabList.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
          activeTab.focus();
        }
      }
    },

    handleTabKeydown(event) {
      const tabs = [...this.elements.tabList.querySelectorAll('[role="tab"]')];
      const currentIndex = tabs.findIndex(tab => tab === document.activeElement);
      if (currentIndex === -1) {
        return;
      }

      let nextIndex = currentIndex;
      if (event.key === 'ArrowRight') {
        nextIndex = (currentIndex + 1) % tabs.length;
      } else if (event.key === 'ArrowLeft') {
        nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (event.key === 'Home') {
        nextIndex = 0;
      } else if (event.key === 'End') {
        nextIndex = tabs.length - 1;
      } else {
        return;
      }

      event.preventDefault();
      this.setActiveTab(tabs[nextIndex].dataset.tab);
    },

    handleKeydown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        this.close();
        return;
      }

      if (event.key !== 'Tab') {
        return;
      }

      const focusable = [...this.elements.dialog.querySelectorAll(FOCUSABLE_SELECTOR)]
        .filter(element => element.offsetParent !== null);
      if (!focusable.length) {
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  };

  global.TicketModal = TicketModal;
  global.TicketDetails = TicketDetails;
  global.TicketTimeline = TicketTimeline;
  global.TimelineItem = TimelineItem;
})(window);

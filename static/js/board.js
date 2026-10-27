/**
 * Project Management System - Kanban Board & UI Controller
 * SRS FR-07, FR-08, FR-10, FR-12, FR-14, NFR-05 (Keyboard Accessibility).
 */

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie('csrftoken');

class KanbanBoard {
  constructor(projectId, isArchived) {
    this.projectId = projectId;
    this.isArchived = isArchived;
    this.tasks = [];
    this.activeTask = null;
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadTasks();
    this.loadDashboard();
  }

  setupEventListeners() {
    // Search input with debounce
    const searchInput = document.getElementById('task-search');
    if (searchInput) {
      let timeout = null;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => this.loadTasks(), 250);
      });
    }

    // Filter dropdowns (FR-08)
    const assigneeFilter = document.getElementById('filter-assignee');
    const priorityFilter = document.getElementById('filter-priority');
    const dueFilter = document.getElementById('filter-due');

    [assigneeFilter, priorityFilter, dueFilter].forEach(el => {
      if (el) el.addEventListener('change', () => this.loadTasks());
    });

    // Column Drag & Drop
    const columnBodies = document.querySelectorAll('.column-body');
    columnBodies.forEach(col => {
      col.addEventListener('dragover', (e) => {
        if (this.isArchived) return;
        e.preventDefault();
        col.classList.add('drag-over');
      });

      col.addEventListener('dragleave', () => col.classList.remove('drag-over'));

      col.addEventListener('drop', (e) => {
        if (this.isArchived) return;
        e.preventDefault();
        col.classList.remove('drag-over');
        const taskId = e.dataTransfer.getData('text/plain');
        const targetStatus = col.dataset.status;
        if (taskId && targetStatus) {
          this.transitionTaskStatus(taskId, targetStatus);
        }
      });
    });

    // Modal Close buttons
    const closeBtns = document.querySelectorAll('.modal-close, .btn-modal-close');
    closeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
      });
    });

    // Global Escape key closes any active modal (NFR-05)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
      }
    });
  }

  async loadTasks() {
    const searchVal = document.getElementById('task-search')?.value || '';
    const assigneeVal = document.getElementById('filter-assignee')?.value || '';
    const priorityVal = document.getElementById('filter-priority')?.value || '';
    const dueVal = document.getElementById('filter-due')?.value || '';

    const params = new URLSearchParams();
    if (searchVal) params.append('q', searchVal);
    if (assigneeVal) params.append('assignee', assigneeVal);
    if (priorityVal) params.append('priority', priorityVal);
    if (dueVal) params.append('due_status', dueVal);

    try {
      const resp = await fetch(`/tasks/projects/${this.projectId}/tasks/?${params.toString()}`, {
        headers: { 'Accept': 'application/json' }
      });
      if (!resp.ok) throw new Error('Failed to load tasks');
      const data = await resp.json();
      this.tasks = data.tasks;
      this.renderBoard();
    } catch (err) {
      console.error(err);
    }
  }

  renderBoard() {
    const columns = {
      'Backlog': document.querySelector('.column-body[data-status="Backlog"]'),
      'To Do': document.querySelector('.column-body[data-status="To Do"]'),
      'In Progress': document.querySelector('.column-body[data-status="In Progress"]'),
      'Review': document.querySelector('.column-body[data-status="Review"]'),
      'Done': document.querySelector('.column-body[data-status="Done"]'),
    };

    // Clear column contents
    Object.keys(columns).forEach(status => {
      if (columns[status]) columns[status].innerHTML = '';
      const countEl = document.querySelector(`.column-count[data-status="${status}"]`);
      if (countEl) countEl.textContent = '0';
    });

    const statusCounts = { 'Backlog': 0, 'To Do': 0, 'In Progress': 0, 'Review': 0, 'Done': 0 };

    this.tasks.forEach(task => {
      if (!columns[task.status]) return;
      statusCounts[task.status] = (statusCounts[task.status] || 0) + 1;

      const card = document.createElement('div');
      card.className = 'task-card';
      card.tabIndex = 0;
      card.setAttribute('role', 'button');
      card.setAttribute('aria-label', `Task ${task.id}: ${task.title}. Status: ${task.status}. Priority: ${task.priority}`);
      card.dataset.taskId = task.id;
      card.dataset.version = task.version;

      if (!this.isArchived) {
        card.draggable = true;
        card.addEventListener('dragstart', (e) => {
          e.dataTransfer.setData('text/plain', task.id);
          card.classList.add('dragging');
        });
        card.addEventListener('dragend', () => card.classList.remove('dragging'));
      }

      card.addEventListener('click', () => this.openTaskDetailModal(task.id));

      // Keyboard support for activating task card (NFR-05)
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.openTaskDetailModal(task.id);
        }
      });

      const priorityClass = `badge-${task.priority.toLowerCase()}`;
      const overdueClass = task.is_overdue ? 'task-overdue' : '';

      card.innerHTML = `
        <div class="task-card-header">
          <span class="task-id">#${task.id}</span>
          <span class="badge ${priorityClass}">${task.priority}</span>
        </div>
        <div class="task-title">${this.escapeHtml(task.title)}</div>
        <div class="task-meta">
          <span>${task.assignee_email ? task.assignee_email.split('@')[0] : 'Unassigned'}</span>
          <span class="${overdueClass}">${task.due_date ? task.due_date : 'No Due Date'}</span>
        </div>
      `;

      columns[task.status].appendChild(card);
    });

    // Update count labels
    Object.keys(statusCounts).forEach(status => {
      const countEl = document.querySelector(`.column-count[data-status="${status}"]`);
      if (countEl) countEl.textContent = statusCounts[status];
    });
  }

  async transitionTaskStatus(taskId, targetStatus) {
    const task = this.tasks.find(t => t.id == taskId);
    if (!task || task.status === targetStatus) return;

    try {
      const resp = await fetch(`/tasks/projects/${this.projectId}/tasks/${taskId}/status/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          status: targetStatus,
          expected_version: task.version // Concurrency check (SAD §3.7)
        })
      });

      if (resp.status === 409) {
        const errorData = await resp.json();
        alert(errorData.error.message || 'Task was updated by another user. Reloading board...');
        this.loadTasks();
        return;
      }

      if (!resp.ok) {
        const err = await resp.json();
        alert(err.error?.message || 'Failed to update status');
        return;
      }

      const updated = await resp.json();
      task.status = updated.status;
      task.version = updated.version;
      this.renderBoard();
      this.loadDashboard();
    } catch (err) {
      console.error(err);
      alert('Network error while updating status');
    }
  }

  async openTaskDetailModal(taskId) {
    try {
      const resp = await fetch(`/tasks/projects/${this.projectId}/tasks/${taskId}/`, {
        headers: { 'Accept': 'application/json' }
      });
      if (!resp.ok) throw new Error('Failed to load task details');
      const task = await resp.json();
      this.activeTask = task;

      document.getElementById('modal-task-title').textContent = `#${task.id}: ${task.title}`;
      document.getElementById('modal-task-desc').textContent = task.description || 'No description provided.';
      document.getElementById('modal-task-status').textContent = task.status;
      document.getElementById('modal-task-priority').textContent = task.priority;
      document.getElementById('modal-task-estimate').textContent = `${task.estimate_hours} hrs`;
      document.getElementById('modal-task-actual').textContent = `${task.actual_hours} hrs`;
      document.getElementById('modal-task-assignee').textContent = task.assignee_email || 'Unassigned';
      document.getElementById('modal-task-due').textContent = task.due_date || 'None';

      // Status selector for keyboard accessibility (NFR-05)
      const statusSelect = document.getElementById('modal-status-select');
      if (statusSelect) {
        statusSelect.value = task.status;
        statusSelect.onchange = () => this.transitionTaskStatus(task.id, statusSelect.value);
      }

      // Render comments (FR-12)
      const commentsList = document.getElementById('modal-comments-list');
      if (commentsList) {
        commentsList.innerHTML = task.comments.map(c => `
          <div style="background: rgba(15,23,42,0.4); padding: 0.6rem; border-radius: 6px; margin-bottom: 0.5rem;">
            <div style="font-size: 0.75rem; color: #94a3b8; display: flex; justify-content: space-between;">
              <span>${c.author}</span>
              <span>${new Date(c.created_at).toLocaleString()}</span>
            </div>
            <div style="margin-top: 0.3rem; font-size: 0.85rem;">${this.escapeHtml(c.text)}</div>
          </div>
        `).join('') || '<p style="font-size: 0.8rem; color: #94a3b8;">No comments yet.</p>';
      }

      // Render Time Logs (FR-10)
      const timeLogsList = document.getElementById('modal-timelogs-list');
      if (timeLogsList) {
        timeLogsList.innerHTML = task.time_entries.map(te => `
          <div style="display: flex; justify-content: space-between; font-size: 0.8rem; padding: 0.4rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
            <span>${te.user} (${te.date}): <strong>${te.hours}h</strong> - ${this.escapeHtml(te.note || 'No note')}</span>
            ${te.is_owner ? `<button onclick="window.kanban.deleteTimeEntry(${task.id}, ${te.id})" class="btn btn-outline" style="padding: 2px 6px; font-size: 0.7rem;">Delete</button>` : ''}
          </div>
        `).join('') || '<p style="font-size: 0.8rem; color: #94a3b8;">No logged time yet.</p>';
      }

      const modalEl = document.getElementById('task-detail-modal');
      modalEl.classList.add('active');

      // Focus status selector or close button for accessible keyboard navigation
      const firstFocusable = modalEl.querySelector('select, button, input');
      if (firstFocusable) {
        firstFocusable.focus();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async postComment(e) {
    e.preventDefault();
    if (!this.activeTask) return;
    const input = document.getElementById('new-comment-text');
    const text = input.value.trim();
    if (!text) return;

    try {
      const resp = await fetch(`/tasks/projects/${this.projectId}/tasks/${this.activeTask.id}/comments/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
          'Accept': 'application/json'
        },
        body: JSON.stringify({ text })
      });
      if (resp.ok) {
        input.value = '';
        this.openTaskDetailModal(this.activeTask.id);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async logTime(e) {
    e.preventDefault();
    if (!this.activeTask) return;
    const hours = document.getElementById('new-time-hours').value;
    const note = document.getElementById('new-time-note').value;

    try {
      const resp = await fetch(`/tasks/projects/${this.projectId}/tasks/${this.activeTask.id}/time/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
          'Accept': 'application/json'
        },
        body: JSON.stringify({ hours, note })
      });
      if (resp.ok) {
        document.getElementById('new-time-hours').value = '';
        document.getElementById('new-time-note').value = '';
        this.openTaskDetailModal(this.activeTask.id);
        this.loadDashboard();
      } else {
        const err = await resp.json();
        alert(err.error?.message || 'Invalid time entry');
      }
    } catch (err) {
      console.error(err);
    }
  }

  async deleteTimeEntry(taskId, entryId) {
    if (!confirm('Delete this time entry?')) return;
    try {
      const resp = await fetch(`/tasks/projects/${this.projectId}/tasks/${taskId}/time/${entryId}/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': csrftoken,
          'Accept': 'application/json'
        }
      });
      if (resp.ok) {
        this.openTaskDetailModal(taskId);
        this.loadDashboard();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async loadDashboard() {
    try {
      const resp = await fetch(`/tasks/projects/${this.projectId}/dashboard/`, {
        headers: { 'Accept': 'application/json' }
      });
      if (!resp.ok) return;
      const data = await resp.json();

      const totalEl = document.getElementById('dash-total-tasks');
      const overdueEl = document.getElementById('dash-overdue-tasks');
      const estEl = document.getElementById('dash-est-hours');
      const actEl = document.getElementById('dash-act-hours');

      if (totalEl) totalEl.textContent = data.total_tasks;
      if (overdueEl) overdueEl.textContent = data.overdue_count;
      if (estEl) estEl.textContent = `${data.estimated_hours}h`;
      if (actEl) actEl.textContent = `${data.actual_hours}h`;
    } catch (err) {
      console.error(err);
    }
  }

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

window.KanbanBoard = KanbanBoard;

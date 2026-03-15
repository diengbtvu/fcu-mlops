/**
 * Admin Panel JavaScript
 * Common functionality for admin tables, modals, and forms
 */

class AdminPanel {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupModals();
        this.setupTables();
        this.setupBulkActions();
        this.setupFormValidation();
    }
    
    setupModals() {
        // Add smooth animations for modals
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('show.bs.modal', function() {
                this.style.display = 'block';
                this.style.opacity = '0';
                setTimeout(() => {
                    this.style.opacity = '1';
                }, 10);
            });
            
            modal.addEventListener('hidden.bs.modal', function() {
                // Reset form inside modal if any
                const form = this.querySelector('form');
                if (form) {
                    form.reset();
                    this.clearValidation(form);
                }
            });
        });
    }
    
    setupTables() {
        // Add loading states for table operations
        const tables = document.querySelectorAll('.table');
        tables.forEach(table => {
            // Handle action buttons
            const actionButtons = table.querySelectorAll('.action-buttons .btn');
            actionButtons.forEach(button => {
                if (button.getAttribute('href') || button.type === 'submit') {
                    button.addEventListener('click', function() {
                        if (!this.disabled) {
                            this.classList.add('loading');
                            this.disabled = true;
                            
                            // Re-enable after 3 seconds as fallback
                            setTimeout(() => {
                                this.classList.remove('loading');
                                this.disabled = false;
                            }, 3000);
                        }
                    });
                }
            });
        });
        
        // Setup table sorting
        this.setupTableSorting();
        
        // Setup table search
        this.setupTableSearch();
    }
    
    setupTableSorting() {
        const sortableHeaders = document.querySelectorAll('[data-sort]');
        sortableHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                const column = header.dataset.sort;
                const table = header.closest('table');
                this.sortTable(table, column);
            });
        });
    }
    
    setupTableSearch() {
        const searchInputs = document.querySelectorAll('[data-table-search]');
        searchInputs.forEach(input => {
            input.addEventListener('input', debounce((e) => {
                const tableId = e.target.dataset.tableSearch;
                const table = document.getElementById(tableId);
                if (table) {
                    this.filterTable(table, e.target.value);
                }
            }, 300));
        });
    }
    
    setupBulkActions() {
        const masterCheckbox = document.querySelector('[data-master-checkbox]');
        const bulkCheckboxes = document.querySelectorAll('[data-bulk-checkbox]');
        const bulkActions = document.querySelector('.bulk-actions');
        
        if (masterCheckbox && bulkCheckboxes.length > 0) {
            masterCheckbox.addEventListener('change', () => {
                bulkCheckboxes.forEach(checkbox => {
                    checkbox.checked = masterCheckbox.checked;
                });
                this.updateBulkActions();
            });
            
            bulkCheckboxes.forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    this.updateBulkActions();
                });
            });
        }
    }
    
    setupFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });
    }
    
    sortTable(table, column) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isAscending = table.dataset.sortDirection !== 'asc';
        
        rows.sort((a, b) => {
            const aValue = a.querySelector(`[data-sort-value="${column}"]`)?.textContent || '';
            const bValue = b.querySelector(`[data-sort-value="${column}"]`)?.textContent || '';
            
            if (isAscending) {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        });
        
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
        
        table.dataset.sortDirection = isAscending ? 'asc' : 'desc';
        
        // Update sort indicators
        const headers = table.querySelectorAll('[data-sort]');
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (header.dataset.sort === column) {
                header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
            }
        });
    }
    
    filterTable(table, searchTerm) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const shouldShow = text.includes(searchTerm.toLowerCase());
            row.style.display = shouldShow ? '' : 'none';
        });
    }
    
    updateBulkActions() {
        const bulkCheckboxes = document.querySelectorAll('[data-bulk-checkbox]');
        const checkedBoxes = document.querySelectorAll('[data-bulk-checkbox]:checked');
        const bulkActions = document.querySelector('.bulk-actions');
        const masterCheckbox = document.querySelector('[data-master-checkbox]');
        
        if (bulkActions) {
            if (checkedBoxes.length > 0) {
                bulkActions.classList.add('show');
                const countElement = bulkActions.querySelector('.selected-count');
                if (countElement) {
                    countElement.textContent = checkedBoxes.length;
                }
            } else {
                bulkActions.classList.remove('show');
            }
        }
        
        if (masterCheckbox) {
            if (checkedBoxes.length === 0) {
                masterCheckbox.indeterminate = false;
                masterCheckbox.checked = false;
            } else if (checkedBoxes.length === bulkCheckboxes.length) {
                masterCheckbox.indeterminate = false;
                masterCheckbox.checked = true;
            } else {
                masterCheckbox.indeterminate = true;
            }
        }
    }
    
    clearValidation(form) {
        form.classList.remove('was-validated');
        const invalidElements = form.querySelectorAll('.is-invalid');
        invalidElements.forEach(element => {
            element.classList.remove('is-invalid');
        });
    }
    
    showToast(message, type = 'success') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Add to toast container or create one
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    confirmAction(message, callback, options = {}) {
        const defaultOptions = {
            title: 'Confirm Action',
            confirmText: 'Yes, Continue',
            cancelText: 'Cancel',
            type: 'warning'
        };
        
        const opts = { ...defaultOptions, ...options };
        
        if (confirm(`${opts.title}\n\n${message}`)) {
            callback();
        }
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    window.adminPanel = new AdminPanel();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminPanel;
}

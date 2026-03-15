/**
 * DataTables Configuration for AdminLTE Integration
 * Hydrogen Production Rate Prediction System
 */

class DataTablesManager {
    constructor() {
        this.defaultConfig = {
            responsive: true,
            lengthChange: true,
            autoWidth: false,
            searching: true,
            ordering: true,
            info: true,
            paging: true,
            pageLength: 25,
            lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
            language: {
                search: "Search:",
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                infoEmpty: "Showing 0 to 0 of 0 entries",
                infoFiltered: "(filtered from _MAX_ total entries)",
                zeroRecords: "No matching records found",
                emptyTable: "No data available in table",
                paginate: {
                    first: "First",
                    last: "Last",
                    next: "Next",
                    previous: "Previous"
                }
            },
            dom: 'Bfrtip',
            buttons: [
                {
                    extend: 'copy',
                    className: 'btn btn-secondary btn-sm'
                },
                {
                    extend: 'csv',
                    className: 'btn btn-success btn-sm'
                },
                {
                    extend: 'excel',
                    className: 'btn btn-success btn-sm'
                },
                {
                    extend: 'pdf',
                    className: 'btn btn-danger btn-sm'
                },
                {
                    extend: 'print',
                    className: 'btn btn-info btn-sm'
                }
            ]
        };
    }

    /**
     * Initialize DataTable for Admin History
     */
    initAdminHistory() {
        const config = {
            ...this.defaultConfig,
            columnDefs: [
                { 
                    targets: [0], 
                    type: 'date',
                    render: function(data, type, row) {
                        if (type === 'display' || type === 'type') {
                            return '<small>' + data + '</small>';
                        }
                        return data;
                    }
                },
                { 
                    targets: [1], 
                    orderable: true,
                    render: function(data, type, row) {
                        return data; // Model name with badge
                    }
                },
                { 
                    targets: [2, 3, 4, 5], 
                    className: 'text-center',
                    render: function(data, type, row) {
                        return '<span class="badge badge-light">' + data + '</span>';
                    }
                },
                { 
                    targets: [6], 
                    className: 'text-center font-weight-bold',
                    render: function(data, type, row) {
                        const value = parseFloat(data.replace('%', ''));
                        let badgeClass = 'badge-success';
                        if (value < 50) badgeClass = 'badge-danger';
                        else if (value < 75) badgeClass = 'badge-warning';
                        
                        return '<span class="badge ' + badgeClass + ' badge-lg">' + data + '</span>';
                    }
                },
                { 
                    targets: [7], 
                    className: 'text-center',
                    orderable: false
                }
            ],
            order: [[0, 'desc']], // Sort by date descending
            buttons: [
                {
                    extend: 'copy',
                    text: '<i class="fas fa-copy"></i> Copy',
                    className: 'btn btn-secondary btn-sm'
                },
                {
                    extend: 'csv',
                    text: '<i class="fas fa-file-csv"></i> CSV',
                    className: 'btn btn-success btn-sm',
                    filename: 'admin_predictions_' + new Date().toISOString().slice(0,10)
                },
                {
                    extend: 'excel',
                    text: '<i class="fas fa-file-excel"></i> Excel',
                    className: 'btn btn-success btn-sm',
                    filename: 'admin_predictions_' + new Date().toISOString().slice(0,10)
                },
                {
                    extend: 'pdf',
                    text: '<i class="fas fa-file-pdf"></i> PDF',
                    className: 'btn btn-danger btn-sm',
                    filename: 'admin_predictions_' + new Date().toISOString().slice(0,10),
                    orientation: 'landscape',
                    pageSize: 'A4'
                },
                {
                    extend: 'print',
                    text: '<i class="fas fa-print"></i> Print',
                    className: 'btn btn-info btn-sm'
                }
            ]
        };

        return $('#admin-history-table').DataTable(config);
    }

    /**
     * Initialize DataTable for Users Management
     */
    initUsersTable() {
        const config = {
            ...this.defaultConfig,
            columnDefs: [
                { targets: [0], className: 'font-weight-bold' },
                { targets: [1], className: 'text-truncate', width: '200px' },
                { targets: [2], className: 'font-weight-bold' },
                { targets: [3], className: 'text-center' },
                { targets: [4], className: 'text-truncate', width: '150px' },
                { 
                    targets: [5], 
                    className: 'text-center',
                    render: function(data, type, row) {
                        const count = parseInt(data);
                        let badgeClass = 'badge-light';
                        if (count > 10) badgeClass = 'badge-success';
                        else if (count > 5) badgeClass = 'badge-warning';
                        else if (count > 0) badgeClass = 'badge-info';
                        
                        return '<span class="badge ' + badgeClass + '">' + count + '</span>';
                    }
                },
                { targets: [6], orderable: false, searchable: false, className: 'text-center' }
            ],
            order: [[0, 'asc']],
            buttons: [
                {
                    extend: 'copy',
                    text: '<i class="fas fa-copy"></i> Copy',
                    className: 'btn btn-secondary btn-sm'
                },
                {
                    extend: 'excel',
                    text: '<i class="fas fa-file-excel"></i> Excel',
                    className: 'btn btn-success btn-sm',
                    filename: 'users_list_' + new Date().toISOString().slice(0,10)
                },
                {
                    extend: 'pdf',
                    text: '<i class="fas fa-file-pdf"></i> PDF',
                    className: 'btn btn-danger btn-sm',
                    filename: 'users_list_' + new Date().toISOString().slice(0,10)
                }
            ]
        };

        return $('#users-table').DataTable(config);
    }

    /**
     * Initialize DataTable for Models Management
     */
    initModelsTable() {
        const config = {
            ...this.defaultConfig,
            columnDefs: [
                { targets: [0], className: 'font-weight-bold' },
                { 
                    targets: [1], 
                    render: function(data, type, row) {
                        return data; // Already formatted with badges
                    }
                },
                { targets: [2], className: 'text-center' },
                { targets: [3], className: 'text-center' },
                { targets: [4], className: 'text-center' },
                { targets: [5], orderable: false, searchable: false, className: 'text-center' }
            ],
            order: [[0, 'asc']],
            buttons: [
                {
                    extend: 'copy',
                    text: '<i class="fas fa-copy"></i> Copy',
                    className: 'btn btn-secondary btn-sm'
                },
                {
                    extend: 'excel',
                    text: '<i class="fas fa-file-excel"></i> Excel',
                    className: 'btn btn-success btn-sm',
                    filename: 'ml_models_' + new Date().toISOString().slice(0,10)
                }
            ]
        };

        return $('#models-table').DataTable(config);
    }

    /**
     * Initialize DataTable for User History
     */
    initUserHistory() {
        const config = {
            ...this.defaultConfig,
            columnDefs: [
                { targets: [0], type: 'date' },
                { targets: [1], orderable: true },
                { targets: [2, 3, 4, 5], className: 'text-center' },
                { 
                    targets: [6], 
                    className: 'text-center font-weight-bold',
                    render: function(data, type, row) {
                        const value = parseFloat(data.replace('%', ''));
                        let color = 'text-success';
                        if (value < 50) color = 'text-danger';
                        else if (value < 75) color = 'text-warning';
                        
                        return '<span class="' + color + '">' + data + '</span>';
                    }
                }
            ],
            order: [[0, 'desc']],
            buttons: [
                {
                    extend: 'copy',
                    text: '<i class="fas fa-copy"></i> Copy',
                    className: 'btn btn-secondary btn-sm'
                },
                {
                    extend: 'csv',
                    text: '<i class="fas fa-file-csv"></i> CSV',
                    className: 'btn btn-success btn-sm',
                    filename: 'my_predictions_' + new Date().toISOString().slice(0,10)
                },
                {
                    extend: 'print',
                    text: '<i class="fas fa-print"></i> Print',
                    className: 'btn btn-info btn-sm'
                }
            ]
        };

        return $('#user-history-table').DataTable(config);
    }

    /**
     * Initialize DataTable based on table ID
     */
    initTable(tableId) {
        switch(tableId) {
            case 'admin-history-table':
                return this.initAdminHistory();
            case 'users-table':
                return this.initUsersTable();
            case 'models-table':
                return this.initModelsTable();
            case 'user-history-table':
                return this.initUserHistory();
            default:
                return $('#' + tableId).DataTable(this.defaultConfig);
        }
    }
}

// Global instance
window.dataTablesManager = new DataTablesManager();

// Initialize on document ready
$(document).ready(function() {
    // Check if DataTables is loaded
    if (typeof $.fn.DataTable !== 'undefined') {
        console.log('DataTables loaded successfully');
        
        // Auto-initialize tables with data-table attribute
        $('[data-table]').each(function() {
            const tableId = $(this).attr('id');
            if (tableId) {
                try {
                    window.dataTablesManager.initTable(tableId);
                    console.log('DataTable initialized for:', tableId);
                } catch (error) {
                    console.error('Error initializing DataTable for', tableId, ':', error);
                }
            }
        });
    } else {
        console.error('DataTables not loaded!');
    }
});

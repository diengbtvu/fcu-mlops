$(document).ready(function() {
    $('#admin-history-table').DataTable({
        responsive: false,
        autoWidth: false,
        lengthChange: true,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
        pageLength: 25,
        order: [[0, 'desc']],
        scrollX: true,
        scrollCollapse: true,
        columnDefs: [
            {
                targets: '_all',
                className: 'text-nowrap'
            }
        ],
        buttons: [
            {
                extend: 'copy',
                text: '<i class="fas fa-copy"></i> Copy',
                className: 'btn btn-secondary btn-sm',
                exportOptions: { columns: ':visible' }
            },
            {
                extend: 'csv',
                text: '<i class="fas fa-file-csv"></i> CSV',
                className: 'btn btn-success btn-sm',
                filename: 'admin_predictions_' + new Date().toISOString().slice(0,10),
                exportOptions: { columns: ':visible' }
            },
            {
                extend: 'pdf',
                text: '<i class="fas fa-file-pdf"></i> PDF',
                className: 'btn btn-danger btn-sm',
                filename: 'admin_predictions_' + new Date().toISOString().slice(0,10),
                orientation: 'landscape',
                pageSize: 'A3',
                exportOptions: { columns: ':visible' }
            },
            {
                extend: 'excel',
                text: '<i class="fas fa-file-excel"></i> Excel',
                className: 'btn btn-success btn-sm',
                filename: 'admin_predictions_' + new Date().toISOString().slice(0,10),
                exportOptions: { columns: ':visible' }
            },
            {
                extend: 'print',
                text: '<i class="fas fa-print"></i> Print',
                className: 'btn btn-info btn-sm',
                exportOptions: { columns: ':visible' }
            },
            {
                extend: 'colvis',
                text: '<i class="fas fa-eye"></i> Columns',
                className: 'btn btn-secondary btn-sm'
            }
        ],
        language: {
            search: 'Search predictions:',
            lengthMenu: 'Show _MENU_ predictions per page',
            info: 'Showing _START_ to _END_ of _TOTAL_ predictions',
            infoEmpty: 'No predictions found',
            infoFiltered: '(filtered from _MAX_ total predictions)',
            emptyTable: 'No admin predictions available',
            zeroRecords: 'No matching predictions found'
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6">>' +
             '<"row"<"col-sm-12 col-md-7"B><"col-sm-12 col-md-5"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>'
    });
});

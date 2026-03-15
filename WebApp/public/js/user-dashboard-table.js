$(document).ready(function() {
    $('#recent-predictions').DataTable({
        responsive: true,
        autoWidth: false,
        lengthChange: false, // Hide length menu
        searching: false, // Hide search box  
        pageLength: 5, // Fixed 5 entries
        paging: false, // Hide pagination since only 5 entries
        info: false, // Hide info text
        order: [[0, 'desc']], // Sort by Date descending (most recent first)
        buttons: [
            {
                extend: 'copy',
                text: '<i class="fas fa-copy"></i> Copy',
                className: 'btn btn-secondary btn-sm',
                exportOptions: {
                    columns: [0, 1, 2, 3, 4, 5, 6] // All columns for dashboard
                }
            },
            {
                extend: 'csv',
                text: '<i class="fas fa-file-csv"></i> CSV',
                className: 'btn btn-success btn-sm',
                filename: 'recent_predictions_' + new Date().toISOString().slice(0,10),
                exportOptions: {
                    columns: [0, 1, 2, 3, 4, 5, 6]
                }
            },
            {
                extend: 'pdf',
                text: '<i class="fas fa-file-pdf"></i> PDF',
                className: 'btn btn-danger btn-sm',
                filename: 'recent_predictions_' + new Date().toISOString().slice(0,10),
                orientation: 'landscape',
                pageSize: 'A4',
                exportOptions: {
                    columns: [0, 1, 2, 3, 4, 5, 6]
                },
                customize: function (doc) {
                    doc.content[1].table.widths = ['15%', '20%', '12%', '12%', '12%', '12%', '17%'];
                    doc.styles.tableHeader.fontSize = 8;
                    doc.defaultStyle.fontSize = 7;
                }
            },
            {
                extend: 'excel',
                text: '<i class="fas fa-file-excel"></i> Excel',
                className: 'btn btn-success btn-sm',
                filename: 'recent_predictions_' + new Date().toISOString().slice(0,10),
                exportOptions: {
                    columns: [0, 1, 2, 3, 4, 5, 6]
                }
            },
            {
                extend: 'print',
                text: '<i class="fas fa-print"></i> Print',
                className: 'btn btn-info btn-sm',
                exportOptions: {
                    columns: [0, 1, 2, 3, 4, 5, 6]
                }
            },
            {
                extend: 'colvis',
                text: '<i class="fas fa-eye"></i> Columns',
                className: 'btn btn-secondary btn-sm',
                columns: ':not(.no-export)'
            }
        ],
        columnDefs: [
            { responsivePriority: 1, targets: 0 }, // Date
            { responsivePriority: 2, targets: 1 }, // Model
            { responsivePriority: 3, targets: 6 }, // Result
            { responsivePriority: 4, targets: 2 }, // pH
        ],
        language: {
            buttons: {
                copy: 'Copy to clipboard',
                csv: 'Export to CSV',
                excel: 'Export to Excel',
                pdf: 'Export to PDF',
                print: 'Print table',
                colvis: 'Column visibility'
            }
        },
        dom: '<"row"<"col-sm-12"B>>' +
             '<"row"<"col-sm-12"tr>>'
    });
});

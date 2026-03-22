<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title', 'Hydrogen Production Rate Prediction System')</title>
    <link rel="icon" type="image/png" href="{{ asset('images/logo-hidro-predict.png') }}">

    {{-- Typography --}}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    
    {{-- External CSS --}}
    <link href="{{ asset('vendor/bootstrap/css/bootstrap.min.css') }}" rel="stylesheet">
    <link href="{{ asset('vendor/bootstrap-icons/bootstrap-icons.min.css') }}" rel="stylesheet">
    <link rel="stylesheet" href="{{ asset('vendor/fontawesome/css/all.min.css') }}">
    <link rel="stylesheet" href="{{ asset('vendor/adminlte/css/adminlte.min.css') }}">
    
    {{-- DataTables CSS --}}
    <link rel="stylesheet" href="{{ asset('plugins/datatables/css/dataTables.bootstrap4.min.css') }}">
    <link rel="stylesheet" href="{{ asset('plugins/datatables/css/buttons.bootstrap4.min.css') }}">
    <link rel="stylesheet" href="{{ asset('plugins/datatables/css/responsive.bootstrap4.min.css') }}">
    
    {{-- Custom CSS --}}
    <link rel="stylesheet" href="{{ asset('css/common-components.css') }}">
    <link rel="stylesheet" href="{{ asset('css/utilities.css') }}">
    <link rel="stylesheet" href="{{ asset('css/app-layout.css') }}">
    <link rel="stylesheet" href="{{ asset('css/hydrogen-theme.css') }}">
    
    @yield('styles')
</head>
<body class="hold-transition sidebar-mini sidebar-fixed-layout hydrogen-theme">
    <div class="wrapper">
        {{-- Header Component --}}
        <x-layout.header />

        {{-- Sidebar Component - Dynamic based on user role --}}
        <aside class="main-sidebar sidebar-dark-primary elevation-4">
            @yield('sidebar')
        </aside>

        {{-- Content Wrapper Component --}}
        <x-layout.content />

        {{-- Footer Component --}}
        <x-layout.footer />
    </div>

    {{-- Logout Modal Component --}}
    <x-auth.logout-modal />

    {{-- JavaScript --}}
    <script src="{{ asset('vendor/jquery/jquery.min.js') }}"></script>
    <script src="{{ asset('vendor/bootstrap/js/bootstrap.bundle.min.js') }}"></script>
    <script src="{{ asset('vendor/adminlte/js/adminlte.min.js') }}"></script>
    
    {{-- DataTables JavaScript --}}
    <script src="{{ asset('plugins/datatables/js/jquery.dataTables.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/dataTables.bootstrap4.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/dataTables.buttons.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/buttons.bootstrap4.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/buttons.html5.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/buttons.print.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/buttons.colVis.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/jszip.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/pdfmake.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/vfs_fonts.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/dataTables.responsive.min.js') }}"></script>
    <script src="{{ asset('plugins/datatables/js/responsive.bootstrap4.min.js') }}"></script>
    
    {{-- Custom JavaScript with global variables --}}
    <script>
        // Global variables for JavaScript
        window.logoutRoute = '{{ route("logout") }}';
        window.csrfToken = '{{ csrf_token() }}';
    </script>
    <script src="{{ asset('js/app-layout.js') }}"></script>
    
    @yield('scripts')
</body>
</html>

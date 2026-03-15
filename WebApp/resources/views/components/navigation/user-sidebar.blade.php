{{-- User Sidebar --}}
<!-- Brand Logo -->
<a href="{{ route('user.dashboard') }}" class="brand-link">
    <img src="{{ asset('images/logo-hidro-predict.png') }}" alt="System Logo" class="brand-image img-circle elevation-3" style="opacity: .9">
    <span class="brand-text font-weight-light">{{ __('user_sidebar.system_name') }}</span>
</a>

<!-- Sidebar -->
<div class="sidebar">
    <!-- Sidebar Menu -->
    <nav class="mt-2">
        <ul class="nav nav-pills nav-sidebar flex-column" data-widget="treeview" role="menu" data-accordion="false">
            @php
                $menuItems = [
                    [
                        'title' => __('user_sidebar.dashboard'),
                        'route' => 'user.dashboard',
                        'icon' => 'fas fa-tachometer-alt'
                    ],
                ];
                
                // Add menu items based on permissions
                if (auth()->user()->hasPermission('make_predictions')) {
                    $menuItems[] = [
                        'title' => __('user_sidebar.make_prediction'),
                        'route' => 'user.predict',
                        'icon' => 'fas fa-calculator'
                    ];
                }
                
                if (auth()->user()->hasPermission('view_history')) {
                    $menuItems[] = [
                        'title' => __('user_sidebar.prediction_history'),
                        'route' => 'user.history',
                        'icon' => 'fas fa-history'
                    ];
                }
                
                if (auth()->user()->hasPermission('manage_dataset')) {
                    $menuItems[] = [
                        'title' => __('user_sidebar.dataset_management'),
                        'route' => 'user.datasets.index',
                        'icon' => 'fas fa-database'
                    ];
                }
                
                if (auth()->user()->hasPermission('manage_models')) {
                    $menuItems[] = [
                        'title' => __('user_sidebar.model_management'),
                        'route' => 'user.models',
                        'icon' => 'fas fa-brain'
                    ];
                }
                
                // Always show Profile and Security
                $menuItems[] = [
                    'title' => __('user_sidebar.profile'),
                    'route' => 'user.profile',
                    'icon' => 'fas fa-user'
                ];
                
                $menuItems[] = [
                    'title' => __('user_sidebar.security'),
                    'route' => 'user.security',
                    'icon' => 'fas fa-lock'
                ];
            @endphp
            
            <x-navigation.sidebar-menu :items="$menuItems" />
        </ul>
    </nav>
    <!-- /.sidebar-menu -->
    
    <!-- Logout Section -->
    <div class="logout-section">
        <ul class="nav nav-pills nav-sidebar flex-column">
            <li class="nav-item logout-btn">
                <a href="#" class="nav-link logout-link" data-bs-toggle="modal" data-bs-target="#logoutModal" data-toggle="modal" data-target="#logoutModal">
                    <i class="nav-icon fas fa-sign-out-alt"></i>
                    <p>{{ __('user_sidebar.logout') }}</p>
                </a>
            </li>
        </ul>
    </div>
</div>
<!-- /.sidebar -->

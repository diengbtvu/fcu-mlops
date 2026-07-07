{{-- Admin Sidebar --}}
<!-- Brand Logo -->
<a href="{{ route('admin.dashboard') }}" class="brand-link">
    <img src="{{ asset('images/logo-hidro-predict.png') }}" alt="System Logo" class="brand-image img-circle elevation-3" style="opacity: .9">
    <span class="brand-text font-weight-light">{{ __('sidebar.system_name') }}</span>
</a>

<!-- Sidebar -->
<div class="sidebar">
    <!-- Sidebar Menu -->
    <nav class="mt-2">
        <ul class="nav nav-pills nav-sidebar flex-column" data-widget="treeview" role="menu" data-accordion="false">
            <x-navigation.sidebar-menu :items="[
                [
                    'title' => __('sidebar.dashboard'),
                    'route' => 'admin.dashboard',
                    'icon' => 'fas fa-tachometer-alt'
                ],
                [
                    'title' => __('sidebar.make_prediction'),
                    'route' => 'admin.predict',
                    'icon' => 'fas fa-calculator'
                ],
                [
                    'title' => __('sidebar.prediction_history'),
                    'route' => 'admin.history',
                    'icon' => 'fas fa-history'
                ],
                [
                    'title' => __('sidebar.user_management'),
                    'route' => 'admin.users',
                    'icon' => 'fas fa-users'
                ],
                [
                    'title' => __('sidebar.roles_permissions'),
                    'route' => 'admin.roles',
                    'icon' => 'fas fa-shield-alt'
                ],
                [
                    'title' => __('sidebar.model_management'),
                    'route' => 'admin.models',
                    'icon' => 'fas fa-brain'
                ],
                [
                    'title' => __('sidebar.dataset_management'),
                    'route' => 'admin.datasets.index',
                    'icon' => 'fas fa-database'
                ],
                [
                    'title' => __('sidebar.email_settings'),
                    'route' => 'admin.settings.email',
                    'icon' => 'fas fa-envelope'
                ],
                [
                    'title' => __('sidebar.ai_api_keys'),
                    'route' => 'admin.settings.ai',
                    'icon' => 'fas fa-key'
                ],
            ]" />
        </ul>
    </nav>
    <!-- /.sidebar-menu -->
    
    <!-- Logout Section -->
    <div class="logout-section">
        <ul class="nav nav-pills nav-sidebar flex-column">
            <li class="nav-item">
                <a href="{{ route('admin.profile') }}" class="nav-link {{ Request::is('admin/profile*') ? 'active' : '' }}">
                    <i class="nav-icon fas fa-user-circle"></i>
                    <p>{{ __('sidebar.my_profile') }}</p>
                </a>
            </li>
            <li class="nav-item logout-btn">
                <a href="#" class="nav-link logout-link" data-bs-toggle="modal" data-bs-target="#logoutModal" data-toggle="modal" data-target="#logoutModal">
                    <i class="nav-icon fas fa-sign-out-alt"></i>
                    <p>{{ __('sidebar.logout') }}</p>
                </a>
            </li>
        </ul>
    </div>
</div>
<!-- /.sidebar -->

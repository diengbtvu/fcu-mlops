@extends('layouts.app')

@section('title', __('dashboard.admin_dashboard'))
@section('page-title', __('dashboard.title'))

@section('breadcrumb')
    <li class="breadcrumb-item active">{{ __('dashboard.title') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="dashboard-hero">
    <div class="dashboard-hero-eyebrow">{{ __('dashboard.hero_eyebrow') }}</div>
    <h2>{{ __('dashboard.hero_title') }}</h2>
    <p>{{ __('dashboard.hero_desc') }}</p>
    <span class="hero-chip"><i class="fas fa-users"></i> {{ __('dashboard.hero_chip_users', ['count' => $totalUsers]) }}</span>
    <span class="hero-chip"><i class="fas fa-brain"></i> {{ __('dashboard.hero_chip_models', ['count' => $totalModels]) }}</span>
    <span class="hero-chip"><i class="fas fa-check-circle"></i> {{ __('dashboard.hero_chip_active', ['count' => $activeModels]) }}</span>
    <span class="hero-chip"><i class="fas fa-chart-line"></i> {{ __('dashboard.hero_chip_predictions', ['count' => $adminPredictions]) }}</span>
</div>

<div class="row">
    <!-- Statistics using Small Box Components -->
    <x-ui.small-box 
        color="info" 
        :value="$totalUsers" 
        :label="__('dashboard.total_users')" 
        icon="fas fa-users" 
        :link="route('admin.users')" 
        :linkText="__('dashboard.more_info')" />
    
    <x-ui.small-box 
        color="success" 
        :value="$totalModels" 
        :label="__('dashboard.ml_models')" 
        icon="fas fa-brain" 
        :link="route('admin.models')" 
        :linkText="__('dashboard.more_info')" />
    
    <x-ui.small-box 
        color="warning" 
        :value="$activeModels" 
        :label="__('dashboard.active_models')" 
        icon="fas fa-check-circle" 
        :link="route('admin.models')" 
        :linkText="__('dashboard.more_info')" />
    
    <x-ui.small-box 
        color="danger" 
        :value="$adminPredictions" 
        :label="__('dashboard.admin_predictions')" 
        icon="fas fa-calculator" 
        :link="route('admin.history')" 
        :linkText="__('dashboard.view_history')" />
</div>

<div class="row">
    <div class="col-12">
        <x-ui.card :title="__('dashboard.system_overview')">
            <p>{{ __('dashboard.welcome_message') }}</p>
            
            <div class="row">
                <div class="col-md-6">
                    <h5><i class="fas fa-cogs text-primary"></i> {{ __('dashboard.management_features') }}</h5>
                    <ul>
                        <li><strong>{{ __('dashboard.user_management') }}:</strong> {{ __('dashboard.user_management_desc') }}</li>
                        <li><strong>{{ __('dashboard.model_management') }}:</strong> {{ __('dashboard.model_management_desc') }}</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h5><i class="fas fa-calculator text-success"></i> {{ __('dashboard.prediction_features') }}</h5>
                    <ul>
                        <li><strong>{{ __('dashboard.make_predictions') }}:</strong> {{ __('dashboard.make_predictions_desc') }}</li>
                        <li><strong>{{ __('dashboard.view_history') }}:</strong> {{ __('dashboard.view_history_desc') }}</li>
                    </ul>
                </div>
            </div>
            
            <div class="mt-3">
                <a href="{{ route('admin.predict') }}" class="btn btn-success me-2">
                    <i class="fas fa-calculator"></i> {{ __('dashboard.make_prediction') }}
                </a>
                <a href="{{ route('admin.history') }}" class="btn btn-info">
                    <i class="fas fa-history"></i> {{ __('dashboard.view_history') }}
                </a>
            </div>
        </x-ui.card>
    </div>
</div>
@endsection

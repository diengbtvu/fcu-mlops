@extends('layouts.app')

@section('title', __('user_dashboard.title'))
@section('page-title', __('user_dashboard.dashboard'))

@section('breadcrumb')
    <li class="breadcrumb-item active">{{ __('user_dashboard.dashboard') }}</li>
@endsection

@section('sidebar')
    <x-navigation.user-sidebar />
@endsection

@section('content')
<div class="dashboard-hero">
    <div class="dashboard-hero-eyebrow">{{ __('user_dashboard.hero_eyebrow') }}</div>
    <h2>{{ __('user_dashboard.hero_title') }}</h2>
    <p>{{ __('user_dashboard.hero_desc') }}</p>
    <span class="hero-chip"><i class="fas fa-chart-line"></i> {{ __('user_dashboard.hero_chip_predictions', ['count' => $totalPredictions]) }}</span>
    <span class="hero-chip"><i class="fas fa-history"></i> {{ __('user_dashboard.hero_chip_recent', ['count' => $recentPredictions->count()]) }}</span>
    <span class="hero-chip"><i class="fas fa-flask"></i> {{ __('user_dashboard.hero_chip_features', ['count' => 11]) }}</span>
</div>

<div class="row">
    <x-ui.small-box
        color="info"
        :value="$totalPredictions"
        :label="__('user_dashboard.total_predictions')"
        icon="fas fa-calculator"
        :link="route('user.history')"
        :linkText="__('user_dashboard.view_history')" />

    <x-ui.small-box
        color="success"
        :value="__('user_dashboard.make_new')"
        :label="__('user_dashboard.prediction')"
        icon="fas fa-plus-circle"
        :link="route('user.predict')"
        :linkText="__('user_dashboard.start_predicting')" />
</div>

<div class="row">
    <div class="col-12">
        <x-ui.card :title="__('user_dashboard.recent_predictions')">
            @if($recentPredictions->count() > 0)
                <div class="table-responsive">
                    <table id="recent-predictions" class="table table-bordered table-striped">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Model</th>
                                <th>pH</th>
                                <th>VSS</th>
                                <th>Ethanol</th>
                                <th>Acetate</th>
                                <th>HPR (L/h/L)</th>
                            </tr>
                        </thead>
                        <tbody>
                            @foreach($recentPredictions as $prediction)
                            <tr>
                                <td>{{ $prediction->created_at->format('Y-m-d H:i') }}</td>
                                <td>{{ $prediction->mlModel->MLMName }}</td>
                                <td>{{ $prediction->pH }}</td>
                                <td>{{ $prediction->VSS }}</td>
                                <td>{{ $prediction->Ethanol }}</td>
                                <td>{{ $prediction->Acetate }}</td>
                                <td><strong>{{ number_format($prediction->HPR, 4) }}</strong></td>
                            </tr>
                            @endforeach
                        </tbody>
                    </table>
                </div>
            @else
                <div class="text-center py-4">
                    <i class="fas fa-inbox text-muted icon-48"></i>
                    <h5 class="text-muted mt-2">No predictions yet</h5>
                    <p class="text-muted">Start your first Hydrogen prediction.</p>
                    <a href="{{ route('user.predict') }}" class="btn btn-primary">
                        <i class="fas fa-calculator me-1"></i>
                        Make Prediction
                    </a>
                </div>
            @endif
        </x-ui.card>
    </div>
</div>

<div class="row">
    <div class="col-12">
        <x-ui.card title="About Hydrogen Production Rate Prediction">
            <p>This system uses machine learning models to predict Hydrogen Production Rate (HPR) from 11 biochemical features:</p>
            <ul>
                <li><strong>Core chemistry:</strong> pH, VSS, Ethanol, Acetate, Propionate, Butyrate</li>
                <li><strong>Process indicators:</strong> Sucrose Degradation, ORP Mid, ORP Low, VFA, COD-O</li>
                <li><strong>Output:</strong> Predicted HPR in L/h/L</li>
            </ul>
            <p>Use realistic values within the guided ranges to improve prediction reliability.</p>
        </x-ui.card>
    </div>
</div>
@endsection

@section('styles')
<link rel="stylesheet" href="{{ asset('css/admin-tables.css') }}">
@endsection

@section('scripts')
<script src="{{ asset('js/user-dashboard-table.js') }}"></script>
@endsection

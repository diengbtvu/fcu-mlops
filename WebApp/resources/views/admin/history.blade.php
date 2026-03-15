@extends('layouts.app')

@section('title', __('history.title_admin'))
@section('page-title', __('history.title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item active">{{ __('history.breadcrumb') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('styles')
<link rel="stylesheet" href="{{ asset('css/admin-tables.css') }}">
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        <div class="card admin-predictions">
            <div class="card-header">
                <h3 class="card-title">
                    Admin Prediction History
                    <span class="admin-badge">ADMIN</span>
                </h3>
                <div class="card-tools">
                    <a href="{{ route('admin.predict') }}" class="btn btn-primary btn-sm">
                        <i class="bi bi-plus"></i> New Prediction
                    </a>
                </div>
            </div>
            <div class="card-body">
                @if($predictions->count() > 0)
                    <div class="table-responsive">
                        <table id="admin-history-table" class="table table-bordered table-striped">
                            <thead>
                                <tr>
                                    <th>Date & Time</th>
                                    <th>Model</th>
                                    <th>pH</th>
                                    <th>VSS</th>
                                    <th>Ethanol</th>
                                    <th>Acetate</th>
                                    <th>Propionate</th>
                                    <th>Butyrate</th>
                                    <th>Sucrose Degradation</th>
                                    <th>ORP Mid</th>
                                    <th>ORP Low</th>
                                    <th>VFA</th>
                                    <th>COD-O</th>
                                    <th>HPR (L/h/L)</th>
                                    <th>Access Type</th>
                                </tr>
                            </thead>
                            <tbody>
                                @foreach($predictions as $prediction)
                                <tr>
                                    <td>{{ $prediction->created_at->format('Y-m-d H:i:s') }}</td>
                                    <td>
                                        <span class="badge badge-info">{{ $prediction->mlModel->MLMName }}</span>
                                        <br><small class="text-muted">{{ $prediction->mlModel->LibType }}</small>
                                    </td>
                                    <td>{{ $prediction->pH }}</td>
                                    <td>{{ $prediction->VSS }}</td>
                                    <td>{{ $prediction->Ethanol }}</td>
                                    <td>{{ $prediction->Acetate }}</td>
                                    <td>{{ $prediction->Propionate }}</td>
                                    <td>{{ $prediction->Butyrate }}</td>
                                    <td>{{ $prediction->Sucrose_Degradation }}</td>
                                    <td>{{ $prediction->ORP_Mid }}</td>
                                    <td>{{ $prediction->ORP_Low }}</td>
                                    <td>{{ $prediction->VFA }}</td>
                                    <td>{{ $prediction->COD_O }}</td>
                                    <td>{{ number_format($prediction->HPR, 4) }}</td>
                                    <td>
                                        <span class="badge badge-danger">
                                            <i class="bi bi-shield-fill-check"></i> ADMIN
                                        </span>
                                    </td>
                                </tr>
                                @endforeach
                            </tbody>
                        </table>
                    </div>
                @else
                    <div class="text-center py-4">
                        <i class="bi bi-clock-history icon-64 text-muted-light"></i>
                        <h4 class="mt-3">No predictions yet</h4>
                        <p class="text-muted">Create your first Hydrogen prediction.</p>
                        <a href="{{ route('admin.predict') }}" class="btn btn-primary">
                            <i class="bi bi-calculator"></i> Make First Prediction
                        </a>
                    </div>
                @endif
            </div>
        </div>
    </div>
</div>

@if($predictions->count() > 0)
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">Admin Prediction Statistics</h3>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <div class="info-box">
                            <span class="info-box-icon bg-info"><i class="bi bi-calculator"></i></span>
                            <div class="info-box-content">
                                <span class="info-box-text">Total Admin Predictions</span>
                                <span class="info-box-number">{{ $predictions->total() }}</span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-box">
                            <span class="info-box-icon bg-success"><i class="bi bi-graph-up"></i></span>
                            <div class="info-box-content">
                                <span class="info-box-text">Average HPR</span>
                                <span class="info-box-number">{{ number_format($predictions->avg('HPR'), 4) }}</span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-box">
                            <span class="info-box-icon bg-warning"><i class="bi bi-arrow-up"></i></span>
                            <div class="info-box-content">
                                <span class="info-box-text">Highest HPR</span>
                                <span class="info-box-number">{{ number_format($predictions->max('HPR'), 4) }}</span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-box">
                            <span class="info-box-icon bg-danger"><i class="bi bi-arrow-down"></i></span>
                            <div class="info-box-content">
                                <span class="info-box-text">Lowest HPR</span>
                                <span class="info-box-number">{{ number_format($predictions->min('HPR'), 4) }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
@endif
@endsection

@section('scripts')
<script src="{{ asset('js/admin-history-table.js') }}"></script>
@endsection

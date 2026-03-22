@extends('layouts.app')

@section('sidebar')
@if(auth()->user()->role_id == 1)
    <x-navigation.admin-sidebar />
@else
    <x-navigation.user-sidebar />
@endif
@endsection

@section('content')
@php
    $routePrefix = auth()->user()->role_id == 1 ? 'admin' : 'user';
    $validationBadgeClass = ($preview['is_valid'] ?? false) ? 'bg-success' : 'bg-warning text-dark';
    $validationLabel = ($preview['is_valid'] ?? false) ? __('datasets.valid_dataset') : __('datasets.invalid_dataset');
@endphp
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0">{{ __('datasets.dataset_details') }}</h2>
        <a href="{{ route($routePrefix . '.datasets.index') }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {{ __('back') }}
        </a>
    </div>

    <div class="card mb-4">
        <div class="card-header bg-primary text-white">
            <h5 class="mb-0">{{ __('datasets.dataset_information') }}</h5>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>{{ __('datasets.dataset_name') }}:</strong> {{ $dataset->DatasetName }}</p>
                    <p><strong>{{ __('datasets.description') }}:</strong> {{ $dataset->Description ?? __('none') }}</p>
                    <p><strong>{{ __('datasets.uploaded_by') }}:</strong> {{ $dataset->user->FullName ?? __('datasets.unknown_user') }}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>{{ __('datasets.upload_date') }}:</strong> {{ $dataset->UploadDate }}</p>
                    <p><strong>{{ __('datasets.file_path') }}:</strong> <code>{{ $dataset->FilePath }}</code></p>
                    <p><strong>{{ __('datasets.selected_sheet') }}:</strong> {{ $dataset->SelectedSheet ?: __('datasets.csv_default_sheet') }}</p>
                    <p class="mb-0">
                        <strong>{{ __('datasets.latest_trained_model') }}:</strong>
                        {{ $latestTrainedModel?->MLMName ?? __('models.na') }}
                    </p>
                </div>
            </div>
        </div>
    </div>

    @if ($previewError)
        <div class="alert alert-warning">
            <strong>{{ __('warning') }}:</strong> {{ $previewError }}
        </div>
    @elseif ($preview)
        <div class="card mb-4">
            <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">{{ __('datasets.dataset_preview') }}</h5>
                <span class="badge {{ $validationBadgeClass }}">{{ $validationLabel }}</span>
            </div>
            <div class="card-body">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <p class="mb-1"><strong>{{ __('datasets.detected_format') }}:</strong> {{ strtoupper($preview['detected_format'] ?? 'N/A') }}</p>
                        <p class="mb-1"><strong>{{ __('datasets.preview_sheet') }}:</strong> {{ $preview['preview_sheet'] ?? __('datasets.csv_default_sheet') }}</p>
                        <p class="mb-0"><strong>{{ __('datasets.available_sheets') }}:</strong> {{ implode(', ', $preview['sheet_names'] ?? []) }}</p>
                    </div>
                    <div class="col-md-6">
                        <p class="mb-1"><strong>{{ __('datasets.rows_after_preprocessing') }}:</strong> {{ $preview['rows_after_preprocessing'] ?? 0 }}</p>
                        <p class="mb-1"><strong>{{ __('datasets.minimum_required_rows') }}:</strong> {{ $preview['minimum_required_rows'] ?? 6 }}</p>
                        <p class="mb-0"><strong>{{ __('datasets.preview_note') }}:</strong> {{ __('datasets.preview_note_text') }}</p>
                    </div>
                </div>

                @if (!empty($preview['missing_columns']))
                    <div class="alert alert-danger">
                        <strong>{{ __('datasets.missing_required_columns') }}</strong>
                        <div class="mt-2">
                            @foreach ($preview['missing_columns'] as $column)
                                <span class="badge bg-danger me-1 mb-1">{{ $column }}</span>
                            @endforeach
                        </div>
                    </div>
                @endif

                @if (!empty($preview['validation_error']))
                    <div class="alert alert-warning">
                        {{ $preview['validation_error'] }}
                    </div>
                @endif

                @if (!empty($preview['preview_columns']))
                    <div class="table-responsive">
                        <table class="table table-bordered table-sm align-middle">
                            <thead class="table-light">
                                <tr>
                                    @foreach ($preview['preview_columns'] as $column)
                                        <th>{{ $column }}</th>
                                    @endforeach
                                </tr>
                            </thead>
                            <tbody>
                                @forelse (($preview['preview_rows'] ?? []) as $row)
                                    <tr>
                                        @foreach ($preview['preview_columns'] as $column)
                                            <td>{{ $row[$column] ?? '' }}</td>
                                        @endforeach
                                    </tr>
                                @empty
                                    <tr>
                                        <td colspan="{{ count($preview['preview_columns']) }}" class="text-center text-muted">
                                            {{ __('datasets.no_preview_rows') }}
                                        </td>
                                    </tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                @endif
            </div>
        </div>
    @endif

    <div class="d-flex gap-2">
        <a href="{{ route($routePrefix . '.datasets.train.form', $dataset->DatasetId) }}" class="btn btn-success">
            <i class="bi bi-cpu"></i> {{ __('datasets.train_model') }}
        </a>
        @if (!empty($trainingBundleUrl))
            <a href="{{ $trainingBundleUrl }}" class="btn btn-secondary" target="_blank" rel="noopener">
                <i class="bi bi-file-earmark-zip"></i> {{ __('datasets.download_training_bundle') }}
            </a>
        @endif
        <a href="{{ route($routePrefix . '.datasets.augment.form', $dataset->DatasetId) }}" class="btn btn-warning">
            <i class="bi bi-database-add"></i> {{ __('datasets.augment') }}
        </a>
    </div>
</div>
@endsection

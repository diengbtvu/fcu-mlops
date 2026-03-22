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
@endphp
<div class="container">
    <h2>{{ __('datasets.title') }}</h2>
    <a href="{{ route($routePrefix . '.datasets.create') }}" class="btn btn-primary mb-3">{{ __('datasets.upload_new') }}</a>

    @if (session('success'))
    <div class="alert alert-success">{{ session('success') }}</div>
    @endif

    @if (session('error'))
    <div class="alert alert-danger">{{ session('error') }}</div>
    @endif

    <table class="table table-bordered">
        <thead>
            <tr>
                <th>{{ __('datasets.name') }}</th>
                <th>{{ __('datasets.description') }}</th>
                <th>{{ __('datasets.uploaded_by') }}</th>
                <th>{{ __('datasets.upload_date') }}</th>
                <th>{{ __('actions') }}</th>
            </tr>
        </thead>
        <tbody>
            @foreach ($datasets as $dataset)
            <tr>
                <td>{{ $dataset->DatasetName }}</td>
                <td>{{ $dataset->Description }}</td>
                <td>{{ $dataset->user->FullName ?? __('datasets.unknown_user') }}</td>
                <td>{{ $dataset->UploadDate }}</td>
                <td>
                    <a href="{{ route($routePrefix . '.datasets.show', $dataset->DatasetId) }}"
                        class="btn btn-info btn-sm">
                        <i class="bi bi-table"></i> {{ __('datasets.view_data') }}
                    </a>

                    <!-- Nút Train Model -->
                    <a href="{{ route($routePrefix . '.datasets.train.form', $dataset->DatasetId) }}"
                        class="btn btn-success btn-sm">
                        <i class="bi bi-cpu"></i> {{ __('datasets.train_model') }}
                    </a>

                    @if (!empty($trainingBundleUrls[$dataset->DatasetId]))
                        <a href="{{ $trainingBundleUrls[$dataset->DatasetId] }}"
                            class="btn btn-secondary btn-sm"
                            target="_blank"
                            rel="noopener">
                            <i class="bi bi-file-earmark-zip"></i> {{ __('datasets.download_training_bundle') }}
                        </a>
                    @endif

                    <!-- Nút Data Augmentation -->
                    <a href="{{ route($routePrefix . '.datasets.augment.form', $dataset->DatasetId) }}"
                        class="btn btn-warning btn-sm"
                        title="{{ __('datasets.data_augmentation') }}">
                        <i class="bi bi-database-add"></i> {{ __('datasets.augment') }}
                    </a>

                    <form action="{{ route($routePrefix . '.datasets.destroy', $dataset->DatasetId) }}" method="POST" class="d-inline">
                        @csrf
                        @method('DELETE')
                        <button class="btn btn-danger btn-sm" onclick="return confirm(@js(__('datasets.delete_confirm')))">{{ __('delete') }}</button>
                    </form>
                </td>
            </tr>
            @endforeach
        </tbody>
    </table>
</div>
@endsection

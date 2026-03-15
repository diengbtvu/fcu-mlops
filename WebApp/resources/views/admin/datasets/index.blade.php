@extends('layouts.app')

@section('sidebar')
@if(auth()->user()->role_id == 1)
    <x-navigation.admin-sidebar />
@else
    <x-navigation.user-sidebar />
@endif
@endsection

@section('content')
<div class="container">
    <h2>{{ __('datasets.title') }}</h2>
    <a href="{{ route('admin.datasets.create') }}" class="btn btn-primary mb-3">{{ __('datasets.upload_new') }}</a>

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
                    <!-- <a href="{{ route('admin.datasets.show', $dataset->DatasetId) }}" class="btn btn-info btn-sm">{{ __('datasets.details') }}</a> -->

                    <!-- Nút Train Model -->
                    <a href="{{ route('admin.datasets.train.form', $dataset->DatasetId) }}"
                        class="btn btn-success btn-sm">
                        <i class="bi bi-cpu"></i> {{ __('datasets.train_model') }}
                    </a>

                    <!-- Nút Data Augmentation -->
                    <a href="{{ route('admin.datasets.augment.form', $dataset->DatasetId) }}"
                        class="btn btn-warning btn-sm"
                        title="{{ __('datasets.data_augmentation') }}">
                        <i class="bi bi-database-add"></i> {{ __('datasets.augment') }}
                    </a>

                    <form action="{{ route('admin.datasets.destroy', $dataset->DatasetId) }}" method="POST" class="d-inline">
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
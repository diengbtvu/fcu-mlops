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
    <h2>{{ __('datasets.upload_dataset') }}</h2>

    @if ($errors->any())
        <div class="alert alert-danger">
            <strong>{{ __('error') }}!</strong> {{ __('datasets.error_check_input') }}<br><br>
            <ul>
                @foreach ($errors->all() as $error)
                    <li>{{ $error }}</li>
                @endforeach
            </ul>
        </div>
    @endif

    <form action="{{ route('admin.datasets.store') }}" method="POST" enctype="multipart/form-data">
        @csrf
        <div class="mb-3">
            <label for="DatasetName" class="form-label">{{ __('datasets.name') }}</label>
            <input type="text" name="DatasetName" class="form-control" required>
        </div>

        <div class="mb-3">
            <label for="Description" class="form-label">{{ __('datasets.description_optional') }}</label>
            <textarea name="Description" class="form-control"></textarea>
        </div>

        <div class="mb-3">
            <label for="dataset_file" class="form-label">{{ __('datasets.choose_file') }}</label>
            <input type="file" name="dataset_file" class="form-control" accept=".csv,.xlsx" required>
            <div class="mt-2">
                <span class="small text-muted d-block mb-2">{{ __('datasets.download_templates') }}</span>
                <div class="d-flex flex-wrap gap-2">
                    <a href="{{ asset('templates/template_train.csv') }}" class="btn btn-outline-primary btn-sm" download>
                        {{ __('datasets.download_template_csv') }}
                    </a>
                    <a href="{{ asset('templates/template_train.xlsx') }}" class="btn btn-outline-primary btn-sm" download>
                        {{ __('datasets.download_template_xlsx') }}
                    </a>
                </div>
                <small class="text-muted d-block mt-2">{{ __('datasets.template_note') }}</small>
            </div>
        </div>

        <button type="submit" class="btn btn-success">{{ __('upload') }}</button>
        <a href="{{ route('admin.datasets.index') }}" class="btn btn-secondary">{{ __('back') }}</a>
    </form>
</div>
@endsection

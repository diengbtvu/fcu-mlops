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
            <input type="file" name="dataset_file" class="form-control" accept=".csv,.txt,.xls,.xlsx" required>
        </div>

        <button type="submit" class="btn btn-success">{{ __('upload') }}</button>
        <a href="{{ route('admin.datasets.index') }}" class="btn btn-secondary">{{ __('back') }}</a>
    </form>
</div>
@endsection

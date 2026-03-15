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
    <h2>Chi tiết Dataset</h2>
    <p><strong>Tên:</strong> {{ $dataset->DatasetName }}</p>
    <p><strong>Mô tả:</strong> {{ $dataset->Description ?? 'Không có' }}</p>
    <p><strong>Người upload:</strong> {{ $dataset->user->FullName ?? 'Unknown' }}</p>
    <p><strong>Ngày upload:</strong> {{ $dataset->UploadDate }}</p>
    <p><strong>Đường dẫn file:</strong> {{ $dataset->FilePath }}</p>

    <a href="{{ route('admin.datasets.index') }}" class="btn btn-primary">Quay lại</a>
</div>
@endsection

{{-- Component: AdminLTE Small Box Info Card --}}
@props([
    'color' => 'info',
    'value' => '',
    'label' => '',
    'icon' => 'fas fa-info-circle',
    'link' => null,
    'linkText' => 'More info'
])

@php
    $colorClasses = [
        'info' => 'bg-info',
        'success' => 'bg-success',
        'warning' => 'bg-warning',
        'danger' => 'bg-danger',
        'primary' => 'bg-primary',
        'secondary' => 'bg-secondary',
        'dark' => 'bg-dark',
        'light' => 'bg-light'
    ];
    
    $bgClass = $colorClasses[$color] ?? 'bg-info';
@endphp

<div class="col-lg-3 col-6">
    <div class="small-box {{ $bgClass }}">
        <div class="inner">
            <h3>{{ $value }}</h3>
            <p>{{ $label }}</p>
        </div>
        <div class="icon">
            <i class="{{ $icon }}"></i>
        </div>
        @if($link)
            <a href="{{ $link }}" class="small-box-footer">
                {{ $linkText }} <i class="fas fa-arrow-circle-right"></i>
            </a>
        @endif
    </div>
</div>

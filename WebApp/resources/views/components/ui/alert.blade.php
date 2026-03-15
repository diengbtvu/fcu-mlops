{{-- Component: Alert Messages System --}}
@props(['type' => 'info', 'dismissible' => true, 'icon' => null])

@php
    $alertClasses = [
        'success' => 'alert-success',
        'error' => 'alert-danger',
        'danger' => 'alert-danger',
        'warning' => 'alert-warning',
        'info' => 'alert-info',
        'primary' => 'alert-primary',
        'secondary' => 'alert-secondary',
        'light' => 'alert-light',
        'dark' => 'alert-dark'
    ];
    
    $defaultIcons = [
        'success' => 'bi bi-check-circle-fill',
        'error' => 'bi bi-exclamation-triangle-fill',
        'danger' => 'bi bi-exclamation-triangle-fill',
        'warning' => 'bi bi-exclamation-triangle-fill',
        'info' => 'bi bi-info-circle-fill',
        'primary' => 'bi bi-info-circle-fill',
        'secondary' => 'bi bi-info-circle-fill',
        'light' => 'bi bi-info-circle-fill',
        'dark' => 'bi bi-info-circle-fill'
    ];
    
    $alertClass = $alertClasses[$type] ?? 'alert-info';
    $iconClass = $icon ?: ($defaultIcons[$type] ?? 'bi bi-info-circle-fill');
@endphp

<div class="alert {{ $alertClass }} {{ $dismissible ? 'alert-dismissible' : '' }} fade show" role="alert">
    @if($dismissible)
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    @endif
    
    <div class="d-flex align-items-start">
        <i class="{{ $iconClass }} flex-shrink-0 me-2 icon-aligned"></i>
        <div class="flex-grow-1">
            {{ $slot }}
        </div>
    </div>
</div>

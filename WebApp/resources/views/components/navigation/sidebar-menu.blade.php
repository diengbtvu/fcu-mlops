{{-- Component: Sidebar Navigation Menu --}}
@props([
    'items' => [],
    'activeRoute' => null
])

@php
    $currentRoute = $activeRoute ?: request()->route()->getName();
@endphp

@foreach($items as $item)
    <li class="nav-item">
        @if(isset($item['children']) && !empty($item['children']))
            {{-- Menu with children --}}
            <a href="#" class="nav-link {{ collect($item['children'])->pluck('route')->contains($currentRoute) ? 'active' : '' }}">
                <i class="nav-icon {{ $item['icon'] ?? 'bi bi-circle' }}"></i>
                <p>
                    {{ $item['title'] }}
                    <i class="right bi bi-chevron-left"></i>
                </p>
            </a>
            <ul class="nav nav-treeview">
                @foreach($item['children'] as $child)
                    <li class="nav-item">
                        <a href="{{ route($child['route']) }}" 
                           class="nav-link {{ $currentRoute === $child['route'] ? 'active' : '' }}">
                            <i class="nav-icon {{ $child['icon'] ?? 'bi bi-dot' }}"></i>
                            <p>{{ $child['title'] }}</p>
                        </a>
                    </li>
                @endforeach
            </ul>
        @else
            {{-- Simple menu item --}}
            <a href="{{ route($item['route']) }}" 
               class="nav-link {{ $currentRoute === $item['route'] ? 'active' : '' }}">
                <i class="nav-icon {{ $item['icon'] ?? 'bi bi-circle' }}"></i>
                <p>{{ $item['title'] }}</p>
                @if(isset($item['badge']))
                    <span class="badge badge-{{ $item['badge']['color'] ?? 'info' }} right">
                        {{ $item['badge']['text'] }}
                    </span>
                @endif
            </a>
        @endif
    </li>
@endforeach

{{ $slot }}

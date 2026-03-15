{{-- Component: Card Container --}}
@props([
    'title' => null,
    'subtitle' => null,
    'headerColor' => null,
    'collapsible' => false,
    'collapsed' => false,
    'tools' => []
])

@php
    $headerClass = $headerColor ? "card-header bg-{$headerColor}" : 'card-header';
    $bodyClass = $collapsed ? 'card-body collapse' : 'card-body';
    $cardId = 'card-' . Str::random(8);
@endphp

<div class="card {{ $collapsible ? 'card-outline' : '' }}">
    @if($title || $subtitle || isset($header) || !empty($tools) || $collapsible)
        <div class="{{ $headerClass }}">
            @if($title)
                <h3 class="card-title">{{ $title }}</h3>
                @if($subtitle)
                    <p class="card-subtitle text-muted small mt-1 mb-0">{{ $subtitle }}</p>
                @endif
            @endif
            
            @isset($header)
                {{ $header }}
            @endisset
            
            @if(!empty($tools) || $collapsible)
                <div class="card-tools">
                    @foreach($tools as $tool)
                        @if($tool['type'] === 'button')
                            <button type="button" 
                                    class="btn btn-tool btn-{{ $tool['color'] ?? 'default' }}"
                                    @if(isset($tool['onclick'])) onclick="{{ $tool['onclick'] }}" @endif>
                                <i class="{{ $tool['icon'] }}"></i>
                            </button>
                        @endif
                    @endforeach
                    @if($collapsible)
                        <button type="button" 
                                class="btn btn-tool" 
                                data-bs-toggle="collapse" 
                                data-bs-target="#{{ $cardId }}-body">
                            <i class="bi bi-chevron-{{ $collapsed ? 'down' : 'up' }}"></i>
                        </button>
                    @endif
                </div>
            @endif
        </div>
    @endif
    
    <div class="{{ $bodyClass }}" @if($collapsible) id="{{ $cardId }}-body" @endif>
        {{ $slot }}
    </div>
</div>

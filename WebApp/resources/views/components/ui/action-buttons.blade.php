{{-- Component: Action Buttons Group --}}
@props([
    'actions' => [],
    'size' => 'sm',
    'alignment' => 'start'
])

@php
    $alignmentClasses = [
        'start' => 'justify-content-start',
        'center' => 'justify-content-center',
        'end' => 'justify-content-end'
    ];
    
    $alignClass = $alignmentClasses[$alignment] ?? 'justify-content-start';
@endphp

<div class="action-buttons d-flex {{ $alignClass }} flex-wrap gap-1">
    @foreach($actions as $action)
        @if($action['type'] === 'link')
            <a href="{{ $action['url'] }}" 
               class="btn btn-{{ $action['color'] ?? 'primary' }} btn-{{ $size }}"
               @if(isset($action['tooltip']))
                   title="{{ $action['tooltip'] }}"
                   data-bs-toggle="tooltip"
               @endif>
                @if(isset($action['icon']))
                    <i class="{{ $action['icon'] }}"></i>
                @endif
                @if(isset($action['text']))
                    {{ isset($action['icon']) ? ' ' : '' }}{{ $action['text'] }}
                @endif
            </a>
        @elseif($action['type'] === 'button')
            <button type="button" 
                    class="btn btn-{{ $action['color'] ?? 'primary' }} btn-{{ $size }}"
                    @if(isset($action['onclick'])) onclick="{{ $action['onclick'] }}" @endif
                    @if(isset($action['modal'])) data-bs-toggle="modal" data-bs-target="#{{ $action['modal'] }}" @endif
                    @if(isset($action['tooltip']))
                        title="{{ $action['tooltip'] }}"
                        data-bs-toggle="tooltip"
                    @endif>
                @if(isset($action['icon']))
                    <i class="{{ $action['icon'] }}"></i>
                @endif
                @if(isset($action['text']))
                    {{ isset($action['icon']) ? ' ' : '' }}{{ $action['text'] }}
                @endif
            </button>
        @elseif($action['type'] === 'form')
            <form method="{{ $action['method'] ?? 'POST' }}" 
                  action="{{ $action['url'] }}" 
                  class="d-inline"
                  @if(isset($action['confirm'])) 
                      onsubmit="return confirm('{{ $action['confirm'] }}')"
                  @endif>
                @csrf
                @if(isset($action['method']) && $action['method'] !== 'POST')
                    @method($action['method'])
                @endif
                <button type="submit" 
                        class="btn btn-{{ $action['color'] ?? 'danger' }} btn-{{ $size }}"
                        @if(isset($action['tooltip']))
                            title="{{ $action['tooltip'] }}"
                            data-bs-toggle="tooltip"
                        @endif>
                    @if(isset($action['icon']))
                        <i class="{{ $action['icon'] }}"></i>
                    @endif
                    @if(isset($action['text']))
                        {{ isset($action['icon']) ? ' ' : '' }}{{ $action['text'] }}
                    @endif
                </button>
            </form>
        @endif
    @endforeach
    
    {{ $slot }}
</div>

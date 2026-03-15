{{-- Component: Data Table with Actions --}}
@props([
    'headers' => [],
    'rows' => [],
    'actions' => [],
    'id' => 'dataTable',
    'responsive' => true,
    'striped' => true,
    'bordered' => false,
    'hover' => true,
    'showSearch' => true,
    'showEntries' => true,
    'showPagination' => true
])

@php
    $tableClasses = collect(['table'])
        ->when($striped, fn($c) => $c->push('table-striped'))
        ->when($bordered, fn($c) => $c->push('table-bordered'))
        ->when($hover, fn($c) => $c->push('table-hover'))
        ->when($responsive, fn($c) => $c->push('table-responsive'))
        ->implode(' ');
@endphp

<div class="card">
    <div class="card-header">
        <div class="row align-items-center">
            <div class="col">
                <h3 class="card-title">
                    {{ $title ?? 'Data Table' }}
                </h3>
            </div>
            @if($actions)
                <div class="col-auto">
                    @foreach($actions as $action)
                        @if($action['type'] === 'link')
                            <a href="{{ $action['url'] }}" class="btn btn-{{ $action['color'] ?? 'primary' }} btn-sm">
                                <i class="{{ $action['icon'] ?? 'bi bi-plus' }} me-1"></i>
                                {{ $action['text'] }}
                            </a>
                        @endif
                    @endforeach
                </div>
            @endif
        </div>
    </div>
    <div class="card-body">
        @if($responsive)
            <div class="table-responsive">
        @endif
        
        <table id="{{ $id }}" class="{{ $tableClasses }}">
            <thead>
                <tr>
                    @foreach($headers as $header)
                        <th>{{ $header }}</th>
                    @endforeach
                    @if(!empty($actions))
                        <th width="150">Actions</th>
                    @endif
                </tr>
            </thead>
            <tbody>
                {{ $slot }}
            </tbody>
        </table>
        
        @if($responsive)
            </div>
        @endif
    </div>
</div>

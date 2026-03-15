{{-- Component: Session Messages Display --}}
{{-- Automatically displays session success, error messages and validation errors --}}

@if(session('success'))
    <x-ui.alert type="success" dismissible>
        {{ session('success') }}
    </x-ui.alert>
@endif

@if(session('error'))
    <x-ui.alert type="error" dismissible>
        {{ session('error') }}
    </x-ui.alert>
@endif

@if(session('warning'))
    <x-ui.alert type="warning" dismissible>
        {{ session('warning') }}
    </x-ui.alert>
@endif

@if(session('info'))
    <x-ui.alert type="info" dismissible>
        {{ session('info') }}
    </x-ui.alert>
@endif

@if ($errors->any())
    <x-ui.alert type="danger" dismissible>
        <strong>Please fix the following errors:</strong>
        <ul class="mb-0 mt-2">
            @foreach ($errors->all() as $error)
                <li>{{ $error }}</li>
            @endforeach
        </ul>
    </x-ui.alert>
@endif

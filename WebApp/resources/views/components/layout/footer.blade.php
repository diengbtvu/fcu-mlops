{{-- Component: Layout Footer --}}
@props(['year' => null, 'company' => 'Hydrogen Production Rate Prediction System'])

<footer class="main-footer">
    <strong>Copyright &copy; {{ $year ?? date('Y') }} {{ $company }}.</strong>
    All rights reserved.
    @if($slot->isNotEmpty())
        <div class="float-right d-none d-sm-inline-block">
            {{ $slot }}
        </div>
    @endif
</footer>

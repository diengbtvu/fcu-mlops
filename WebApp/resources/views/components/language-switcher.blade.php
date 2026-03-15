{{-- Language Switcher Component --}}
<div class="dropdown">
    <button class="btn btn-link text-decoration-none dropdown-toggle" type="button" id="languageDropdown" data-bs-toggle="dropdown" aria-expanded="false">
        @php
            $currentLocale = app()->getLocale();
            $languages = config('locales.available_locales', []);
        @endphp
        <span class="me-1">{{ $languages[$currentLocale]['flag'] ?? '🌐' }}</span>
        <span class="d-none d-md-inline">{{ $languages[$currentLocale]['native_name'] ?? 'Language' }}</span>
    </button>
    <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="languageDropdown">
        @foreach($languages as $code => $language)
            <li>
                <a class="dropdown-item {{ $currentLocale === $code ? 'active' : '' }}" 
                   href="{{ route('language.switch', $code) }}">
                    <span class="me-2">{{ $language['flag'] }}</span>
                    {{ $language['native_name'] }}
                    @if($currentLocale === $code)
                        <i class="fas fa-check ms-2"></i>
                    @endif
                </a>
            </li>
        @endforeach
    </ul>
</div>

<style>
    #languageDropdown {
        color: #495057;
        padding: 0.5rem 1rem;
    }
    
    #languageDropdown:hover {
        color: #0d6efd;
    }
    
    .dropdown-menu .dropdown-item.active {
        background-color: #0d6efd;
        color: white;
    }
    
    .dropdown-menu .dropdown-item:hover {
        background-color: #f8f9fa;
    }
    
    .dropdown-menu .dropdown-item.active:hover {
        background-color: #0b5ed7;
    }
</style>

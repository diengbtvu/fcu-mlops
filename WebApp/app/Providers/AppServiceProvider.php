<?php

namespace App\Providers;

use Illuminate\Pagination\Paginator;
use Illuminate\Support\Facades\URL;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // Only force HTTPS when the configured public app URL is actually HTTPS.
        // Local Docker serves plain HTTP on localhost:52025, so forcing HTTPS
        // there breaks asset URLs with SSL errors.
        $appUrlScheme = parse_url((string) config('app.url', ''), PHP_URL_SCHEME);
        if ($this->app->environment('production') && $appUrlScheme === 'https') {
            URL::forceScheme('https');
        }

        // Force Bootstrap pagination views instead of Tailwind default.
        Paginator::useBootstrapFive();
    }
}

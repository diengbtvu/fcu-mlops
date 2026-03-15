<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\App;
use Illuminate\Support\Facades\Session;

class SetLocale
{
    /**
     * Handle an incoming request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Closure  $next
     * @return mixed
     */
    public function handle(Request $request, Closure $next)
    {
        // Check if locale is in session
        if (Session::has('locale')) {
            $locale = Session::get('locale');
        } 
        // Check if locale is in request
        elseif ($request->has('locale')) {
            $locale = $request->get('locale');
            Session::put('locale', $locale);
        } 
        // Check if user has language preference (if authenticated)
        elseif (auth()->check() && auth()->user()->language) {
            $locale = auth()->user()->language;
            Session::put('locale', $locale);
        } 
        // Use default locale
        else {
            $locale = config('app.locale');
        }

        // Validate locale from config
        $availableLocales = array_keys(config('locales.available_locales', ['en' => []]));
        if (!in_array($locale, $availableLocales)) {
            $locale = config('locales.locale', 'en');
        }

        App::setLocale($locale);

        return $next($request);
    }
}

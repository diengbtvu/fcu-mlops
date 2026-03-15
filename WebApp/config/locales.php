<?php

return [
    /*
    |--------------------------------------------------------------------------
    | Available Locales
    |--------------------------------------------------------------------------
    |
    | List all available locales in the application.
    | To add a new language:
    | 1. Create a new JSON file in resources/lang/{locale}.json
    | 2. Add the locale code to the array below
    |
    */
    'available_locales' => [
        'en' => [
            'name' => 'English',
            'flag' => '🇺🇸',
            'native_name' => 'English',
        ],
        // 'vi' => [
        //     'name' => 'Vietnamese',
        //     'flag' => '🇻🇳',
        //     'native_name' => 'Tiếng Việt',
        // ],
        'zh_TW' => [
            'name' => 'Traditional Chinese',
            'flag' => '🇹🇼',
            'native_name' => '繁體中文',
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Default Locale
    |--------------------------------------------------------------------------
    |
    | The default locale that will be used by the translation service provider.
    |
    */
    'locale' => env('APP_LOCALE', 'en'),

    /*
    |--------------------------------------------------------------------------
    | Fallback Locale
    |--------------------------------------------------------------------------
    |
    | The fallback locale determines the locale to use when the current one
    | is not available.
    |
    */
    'fallback_locale' => env('APP_FALLBACK_LOCALE', 'en'),
];

<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

Route::post('/test-upload', function (Request $request) {
    if ($request->hasFile('test_file')) {
        $file = $request->file('test_file');
        
        return response()->json([
            'original_name' => $file->getClientOriginalName(),
            'extension' => $file->getClientOriginalExtension(),
            'mime_type' => $file->getMimeType(),
            'size' => $file->getSize(),
            'is_valid' => $file->isValid(),
        ]);
    }
    
    return response()->json(['error' => 'No file uploaded']);
});

// Test routes for role mismatch functionality
Route::get('/test-admin-access', function () {
    return 'This page requires admin access!';
})->middleware(['auth', 'admin'])->name('test.admin');

Route::get('/test-user-access', function () {
    return 'This page requires user access!';
})->middleware(['auth', 'user'])->name('test.user');

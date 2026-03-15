<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\Api\MLModelController;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| is assigned the "api" middleware group. Enjoy building your API!
|
*/

Route::middleware('auth:sanctum')->get('/user', function (Request $request) {
    return $request->user();
});

// ML Model API Routes
Route::prefix('ml-models')->group(function () {
    Route::get('/', [MLModelController::class, 'index']);
    Route::post('/', [MLModelController::class, 'store']);
    Route::get('/active', [MLModelController::class, 'getActiveModel']);
    Route::get('/{id}', [MLModelController::class, 'show']);
    Route::put('/{id}', [MLModelController::class, 'update']);
    Route::delete('/{id}', [MLModelController::class, 'destroy']);
    Route::put('/{id}/activate', [MLModelController::class, 'activate']);
});

// Health check endpoint
Route::get('/health', function () {
    return response()->json([
        'status' => 'healthy',
        'timestamp' => now(),
        'service' => 'Laravel API'
    ]);
});
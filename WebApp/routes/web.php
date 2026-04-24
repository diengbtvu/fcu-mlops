<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\ForgotPasswordController;
use App\Http\Controllers\Admin\AdminController;
use App\Http\Controllers\DatasetController;
use App\Http\Controllers\MLTrainingController;
use App\Http\Controllers\User\UserController;
use App\Http\Controllers\SettingsController;
use App\Http\Controllers\ModelComparisonController;

// Include test routes for debugging
if (app()->environment('local')) {
    include __DIR__ . '/test.php';
}

// API routes moved to routes/api.php

// Redirect root to login
Route::get('/', function () {
    return redirect()->route('login');
});

// Search route for error pages
Route::get('/search', function () {
    return redirect()->route('login')->with('message', 'Please login to use search functionality.');
})->name('search');

// Language switching route
Route::get('/language/{locale}', function ($locale) {
    $availableLocales = array_keys(config('locales.available_locales', []));
    if (in_array($locale, $availableLocales)) {
        session(['locale' => $locale]);
        
        // If user is authenticated, update their language preference
        if (auth()->check()) {
            auth()->user()->update(['language' => $locale]);
        }
    }
    return redirect()->back();
})->name('language.switch');

// Authentication routes
Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login']);
Route::post('/logout', [AuthController::class, 'logout'])->name('logout');
Route::get('/dashboard', [AuthController::class, 'dashboard'])->name('dashboard');

// Password Reset routes
Route::get('/forgot-password', [ForgotPasswordController::class, 'showForgotPasswordForm'])->name('password.request');
Route::post('/forgot-password', [ForgotPasswordController::class, 'sendResetLinkEmail'])->name('password.email');
Route::get('/reset-password/{token}', [ForgotPasswordController::class, 'showResetPasswordForm'])->name('password.reset');
Route::post('/reset-password', [ForgotPasswordController::class, 'resetPassword'])->name('password.update');

// Admin routes - Now accessible by users with appropriate permissions
Route::prefix('admin')->name('admin.')->middleware(['auth', 'admin'])->group(function () {
    Route::get('/dashboard', [AdminController::class, 'dashboard'])->name('dashboard');
    
    // Admin Profile routes (no permission check needed - admin manages their own profile)
    Route::get('/profile', [AdminController::class, 'profile'])->name('profile');
    Route::put('/profile', [AdminController::class, 'updateProfile'])->name('profile.update');
    Route::put('/profile/password', [AdminController::class, 'updatePassword'])->name('profile.password');

    // User management
    Route::get('/users', [AdminController::class, 'users'])->name('users')->middleware('permission:manage_users');
    Route::get('/users/create', [AdminController::class, 'createUser'])->name('users.create')->middleware('permission:manage_users');
    Route::post('/users', [AdminController::class, 'storeUser'])->name('users.store')->middleware('permission:manage_users');
    Route::get('/users/{user}/edit', [AdminController::class, 'editUser'])->name('users.edit')->middleware('permission:manage_users');
    Route::put('/users/{user}', [AdminController::class, 'updateUser'])->name('users.update')->middleware('permission:manage_users');
    Route::post('/users/{user}/reset-password', [AdminController::class, 'resetPassword'])->name('users.reset-password')->middleware('permission:manage_users');
    Route::delete('/users/{user}', [AdminController::class, 'deleteUser'])->name('users.delete')->middleware('permission:manage_users');
    Route::delete('/users/{user}/force', [AdminController::class, 'forceDeleteUser'])->name('users.force-delete')->middleware('permission:manage_users');
    Route::post('/users/{user}/anonymize', [AdminController::class, 'anonymizeUser'])->name('users.anonymize')->middleware('permission:manage_users');
    
    // User-specific permission management
    Route::get('/users/{user}/permissions', [AdminController::class, 'showUserPermissions'])->name('users.permissions')->middleware('permission:manage_users');
    Route::put('/users/{user}/permissions', [AdminController::class, 'updateUserPermissions'])->name('users.permissions.update')->middleware('permission:manage_users');
    
    // User permission groups (roles) management
    Route::get('/users/{user}/roles', [AdminController::class, 'showUserRoles'])->name('users.roles')->middleware('permission:manage_users');
    Route::put('/users/{user}/roles', [AdminController::class, 'updateUserRoles'])->name('users.roles.update')->middleware('permission:manage_users');

    // Model management
    Route::get('/models', [AdminController::class, 'models'])->name('models')->middleware('permission:manage_models');
    Route::get('/models/create', [AdminController::class, 'createModel'])->name('models.create')->middleware('permission:manage_models');
    Route::post('/models', [AdminController::class, 'storeModel'])->name('models.store')->middleware('permission:manage_models');
    Route::get('/models/{model}/report', [AdminController::class, 'showModelReport'])->name('models.report')->middleware('permission:manage_models');
    Route::get('/models/{model}/benchmark', [AdminController::class, 'showModelBenchmark'])->name('models.benchmark')->middleware('permission:manage_models');
    Route::get('/models/{model}/edit', [AdminController::class, 'editModel'])->name('models.edit')->middleware('permission:manage_models');
    Route::put('/models/{model}', [AdminController::class, 'updateModel'])->name('models.update')->middleware('permission:manage_models');
    Route::delete('/models/{model}', [AdminController::class, 'deleteModel'])->name('models.delete')->middleware('permission:manage_models');
    Route::delete('/models/{model}/force', [AdminController::class, 'forceDeleteModel'])->name('models.force-delete')->middleware('permission:manage_models');
    Route::post('/models/{model}/test', [AdminController::class, 'testModel'])->name('models.test')->middleware('permission:manage_models');

    // Model Comparison routes
    Route::get('/models/compare', [ModelComparisonController::class, 'index'])->name('models.compare');
    Route::get('/models/compare/result', [ModelComparisonController::class, 'compare'])->name('models.compare.result');
    Route::get('/models/compare/data', [ModelComparisonController::class, 'getComparisonData'])->name('models.compare.data');

    // Prediction features for admin
    Route::get('/predict', [AdminController::class, 'predict'])->name('predict')->middleware('permission:make_predictions');
    Route::post('/predict', [AdminController::class, 'makePrediction'])->name('predict.make')->middleware('permission:make_predictions');
    Route::get('/history', [AdminController::class, 'history'])->name('history')->middleware('permission:view_history');

    // Dataset management

    Route::get('/datasets', [DatasetController::class, 'index'])->name('datasets.index')->middleware('permission:manage_dataset');
    Route::get('/datasets/create', [DatasetController::class, 'create'])->name('datasets.create')->middleware('permission:manage_dataset');
    Route::post('/datasets', [DatasetController::class, 'store'])->name('datasets.store')->middleware('permission:manage_dataset');
    Route::get('/datasets/{id}', [DatasetController::class, 'show'])->name('datasets.show')->middleware('permission:manage_dataset');
    Route::delete('/datasets/{id}', [DatasetController::class, 'destroy'])->name('datasets.destroy')->middleware('permission:manage_dataset');
    Route::resource('datasets', DatasetController::class)->middleware('permission:manage_dataset');
    
    // Training routes
    Route::get('/datasets/{id}/train', [DatasetController::class, 'showTrainForm'])->name('datasets.train.form')->middleware('permission:training_model');
    Route::post('/datasets/{id}/train', [DatasetController::class, 'train'])->name('datasets.train')->middleware('permission:training_model');

    // Data Augmentation routes
    Route::get('/datasets/{id}/augment', [DatasetController::class, 'showAugmentForm'])->name('datasets.augment.form')->middleware('permission:manage_dataset');
    Route::post('/datasets/{id}/augment', [DatasetController::class, 'augment'])->name('datasets.augment')->middleware('permission:manage_dataset');

    // Email Settings routes
    Route::get('/settings/email', [SettingsController::class, 'emailSettings'])->name('settings.email');
    Route::put('/settings/email', [SettingsController::class, 'updateEmail'])->name('settings.update-email');
    Route::get('/settings/test-email', [SettingsController::class, 'sendTestEmail'])->name('settings.test-email');

    // Role & Permission management
    Route::get('/roles', [AdminController::class, 'roles'])->name('roles')->middleware('permission:manage_roles');
    Route::get('/roles/{role}', [AdminController::class, 'showRole'])->name('roles.show')->middleware('permission:manage_roles');
    Route::put('/roles/{role}/permissions', [AdminController::class, 'updateRolePermissions'])->name('roles.permissions.update')->middleware('permission:manage_roles');

});

// User routes
Route::prefix('user')->name('user.')->middleware(['auth', 'user'])->group(function () {
    Route::get('/dashboard', [UserController::class, 'dashboard'])->name('dashboard');
    Route::get('/predict', [UserController::class, 'predict'])->name('predict');
    Route::post('/predict', [UserController::class, 'makePrediction'])->name('predict.make');
    Route::get('/history', [UserController::class, 'history'])->name('history');
    Route::get('/profile', [UserController::class, 'profile'])->name('profile');
    Route::put('/profile', [UserController::class, 'updateProfile'])->name('profile.update');
    Route::get('/security', [UserController::class, 'security'])->name('security');
    Route::post('/security/change-password', [UserController::class, 'changePassword'])->name('security.change-password');
    
    // Dataset Management (only for users with manage_dataset permission)
    Route::get('/datasets', [UserController::class, 'datasets'])->name('datasets.index')->middleware('permission:manage_dataset');
    Route::get('/datasets/create', [UserController::class, 'createDataset'])->name('datasets.create')->middleware('permission:manage_dataset');
    Route::post('/datasets', [UserController::class, 'storeDataset'])->name('datasets.store')->middleware('permission:manage_dataset');
    Route::get('/datasets/{id}', [UserController::class, 'showDataset'])->name('datasets.show')->middleware('permission:manage_dataset');
    Route::delete('/datasets/{id}', [UserController::class, 'destroyDataset'])->name('datasets.destroy')->middleware('permission:manage_dataset');
    Route::get('/datasets/{id}/train', [UserController::class, 'showTrainForm'])->name('datasets.train.form')->middleware('permission:training_model');
    Route::post('/datasets/{id}/train', [UserController::class, 'trainDataset'])->name('datasets.train')->middleware('permission:training_model');
    Route::get('/datasets/{id}/augment', [UserController::class, 'showAugmentForm'])->name('datasets.augment.form')->middleware('permission:manage_dataset');
    Route::post('/datasets/{id}/augment', [UserController::class, 'augmentDataset'])->name('datasets.augment')->middleware('permission:manage_dataset');
    
    // Model Management (only for users with manage_models permission)
    Route::get('/models', [UserController::class, 'models'])->name('models')->middleware('permission:manage_models');
    Route::get('/models/create', [UserController::class, 'createModel'])->name('models.create')->middleware('permission:manage_models');
    Route::post('/models', [UserController::class, 'storeModel'])->name('models.store')->middleware('permission:manage_models');
    Route::get('/models/{model}/report', [UserController::class, 'showModelReport'])->name('models.report')->middleware('permission:manage_models');
    Route::get('/models/{model}/benchmark', [UserController::class, 'showModelBenchmark'])->name('models.benchmark')->middleware('permission:manage_models');
    Route::get('/models/{model}/edit', [UserController::class, 'editModel'])->name('models.edit')->middleware('permission:manage_models');
    Route::put('/models/{model}', [UserController::class, 'updateModel'])->name('models.update')->middleware('permission:manage_models');
    Route::delete('/models/{model}', [UserController::class, 'deleteModel'])->name('models.delete')->middleware('permission:manage_models');
    Route::post('/models/{model}/test', [UserController::class, 'testModel'])->name('models.test')->middleware('permission:manage_models');
});

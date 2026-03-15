<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class AdminMiddleware
{
    /**
     * Handle an incoming request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Closure(\Illuminate\Http\Request): (\Illuminate\Http\Response|\Illuminate\Http\RedirectResponse)  $next
     * @return \Illuminate\Http\Response|\Illuminate\Http\RedirectResponse
     */
    public function handle(Request $request, Closure $next)
    {
        if (!Auth::check()) {
            return redirect()->route('login')->with('error', 'Please login to access this page.');
        }

        $user = Auth::user()?->fresh();
        if (!$user) {
            Auth::logout();
            return redirect()->route('login')->with('error', 'Please login to access this page.');
        }
        
        // Allow if user is admin OR has any admin-level permissions
        $isAdmin = $user->role->RoleCode === 'admin';
        $hasAdminPermissions = $user->hasAnyPermission([
            'manage_users',
            'manage_roles', 
            'manage_models',
            'manage_dataset',
            'training_model'
        ]);
        
        if (!$isAdmin && !$hasAdminPermissions) {
            // User has no admin privileges or permissions
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => 'Access denied. Admin privileges or appropriate permissions required.',
                    'role_mismatch' => true,
                    'current_role' => $user->role->RoleCode,
                    'required_role' => 'admin'
                ], 403);
            }
            
            return response()->view('errors.403', [
                'role_mismatch' => true,
                'current_role' => $user->role->RoleCode,
                'required_role' => 'admin',
                'user_name' => $user->FullName
            ], 403);
        }

        return $next($request);
    }
}

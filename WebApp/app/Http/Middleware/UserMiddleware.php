<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class UserMiddleware
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
        
        if ($user->role->RoleCode !== 'user') {
            // If user is logged in but not user role, show role mismatch page
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => 'Access denied. User privileges required.',
                    'role_mismatch' => true,
                    'current_role' => $user->role->RoleCode,
                    'required_role' => 'user'
                ], 403);
            }
            
            return response()->view('errors.403', [
                'role_mismatch' => true,
                'current_role' => $user->role->RoleCode,
                'required_role' => 'user',
                'user_name' => $user->FullName
            ], 403);
        }

        return $next($request);
    }
}

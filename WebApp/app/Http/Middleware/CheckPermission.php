<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class CheckPermission
{
    /**
     * Handle an incoming request.
     *
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     * @param  string  $permission  The permission name required to access the route
     */
    public function handle(Request $request, Closure $next, string $permission): Response
    {
        // Check if user is authenticated
        if (!auth()->check()) {
            return redirect()->route('login')->with('error', __('auth.please_login'));
        }

        // Admin role (role_id = 1) always has full access
        if (auth()->user()->role_id === 1) {
            return $next($request);
        }

        // Check if user has the required permission
        if (!auth()->user()->hasPermission($permission)) {
            abort(403, __('permissions.access_denied'));
        }

        return $next($request);
    }
}

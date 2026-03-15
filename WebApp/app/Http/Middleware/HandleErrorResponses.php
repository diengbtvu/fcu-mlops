<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\Response as ResponseAlias;

class HandleErrorResponses
{
    /**
     * Handle an incoming request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     * @return \Symfony\Component\HttpFoundation\Response
     */
    public function handle(Request $request, Closure $next): ResponseAlias
    {
        $response = $next($request);

        // Handle different HTTP status codes
        switch ($response->getStatusCode()) {
            case 404:
                if ($request->expectsJson()) {
                    return response()->json([
                        'error' => 'Not Found',
                        'message' => 'The requested resource was not found.',
                        'status_code' => 404
                    ], 404);
                }
                return response()->view('errors.404', [
                    'exception' => new \Exception('Page not found')
                ], 404);

            case 403:
                if ($request->expectsJson()) {
                    return response()->json([
                        'error' => 'Forbidden',
                        'message' => 'You do not have permission to access this resource.',
                        'status_code' => 403
                    ], 403);
                }
                return response()->view('errors.403', [
                    'exception' => new \Exception('Access forbidden')
                ], 403);

            case 500:
                if ($request->expectsJson()) {
                    return response()->json([
                        'error' => 'Internal Server Error',
                        'message' => 'Something went wrong on our end.',
                        'status_code' => 500
                    ], 500);
                }
                return response()->view('errors.500', [
                    'exception' => new \Exception('Internal server error')
                ], 500);
        }

        return $response;
    }
}

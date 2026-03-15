<?php

namespace App\Exceptions;

use Illuminate\Foundation\Exceptions\Handler as ExceptionHandler;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Database\Eloquent\ModelNotFoundException;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpException;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;
use Throwable;

class Handler extends ExceptionHandler
{
    /**
     * A list of exception types with their corresponding custom log levels.
     *
     * @var array<class-string<\Throwable>, \Psr\Log\LogLevel::*>
     */
    protected $levels = [
        //
    ];

    /**
     * A list of the exception types that are not reported.
     *
     * @var array<int, class-string<\Throwable>>
     */
    protected $dontReport = [
        //
    ];

    /**
     * A list of the inputs that are never flashed to the session on validation exceptions.
     *
     * @var array<int, string>
     */
    protected $dontFlash = [
        'current_password',
        'password',
        'password_confirmation',
    ];

    /**
     * Register the exception handling callbacks for the application.
     */
    public function register(): void
    {
        $this->reportable(function (Throwable $e) {
            //
        });
    }

    /**
     * Render an exception into an HTTP response.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Throwable  $e
     * @return \Symfony\Component\HttpFoundation\Response
     *
     * @throws \Throwable
     */
    public function render($request, Throwable $e)
    {
        // Handle role mismatch exceptions
        if ($e instanceof \App\Exceptions\RoleMismatchException) {
            return response()->view('errors.403', [
                'role_mismatch' => true,
                'user_name' => auth()->user()->FullName ?? 'Guest',
                'current_role' => $e->getCurrentRole(),
                'required_role' => $e->getRequiredRole(),
            ], 403);
        }

        // Handle 404 errors
        if ($e instanceof NotFoundHttpException) {
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => 'Not Found',
                    'message' => 'The requested resource was not found.',
                    'status_code' => 404
                ], 404);
            }
            
            return response()->view('errors.404', [
                'exception' => $e
            ], 404);
        }

        // Handle 403 errors
        if ($e instanceof AuthorizationException) {
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => 'Forbidden',
                    'message' => $e->getMessage() ?: 'You do not have permission to access this resource.',
                    'status_code' => 403
                ], 403);
            }
            
            return response()->view('errors.403', [
                'exception' => $e
            ], 403);
        }

        // Handle 500 errors
        if ($e instanceof \ErrorException || $e instanceof \Error) {
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => 'Internal Server Error',
                    'message' => config('app.debug') ? $e->getMessage() : 'Something went wrong on our end.',
                    'status_code' => 500
                ], 500);
            }
            
            return response()->view('errors.500', [
                'exception' => $e
            ], 500);
        }

        // Handle HTTP exceptions
        if ($e instanceof HttpException) {
            $statusCode = $e->getStatusCode();
            
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => Response::$statusTexts[$statusCode] ?? 'HTTP Error',
                    'message' => $e->getMessage() ?: 'An HTTP error occurred.',
                    'status_code' => $statusCode
                ], $statusCode);
            }

            // Check if we have a custom error view for this status code
            if (view()->exists("errors.{$statusCode}")) {
                return response()->view("errors.{$statusCode}", [
                    'exception' => $e
                ], $statusCode);
            }
        }

        // Handle Model Not Found exceptions
        if ($e instanceof ModelNotFoundException) {
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => 'Not Found',
                    'message' => 'The requested resource was not found.',
                    'status_code' => 404
                ], 404);
            }
            
            return response()->view('errors.404', [
                'exception' => $e
            ], 404);
        }

        // Handle Validation exceptions
        if ($e instanceof ValidationException) {
            if ($request->expectsJson()) {
                return response()->json([
                    'error' => 'Validation Error',
                    'message' => 'The given data was invalid.',
                    'errors' => $e->errors(),
                    'status_code' => 422
                ], 422);
            }
        }

        return parent::render($request, $e);
    }
}

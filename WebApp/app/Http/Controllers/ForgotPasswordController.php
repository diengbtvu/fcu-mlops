<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Str;
use App\Models\User;
use App\Mail\ResetPasswordMail;
use Carbon\Carbon;

class ForgotPasswordController extends Controller
{
    /**
     * Show the forgot password form
     */
    public function showForgotPasswordForm()
    {
        return view('auth.forgot-password');
    }

    /**
     * Send reset link email
     */
    public function sendResetLinkEmail(Request $request)
    {
        $request->validate([
            'email' => 'required|email',
        ]);

        // Find user by email
        $user = User::where('email', $request->email)->first();

        // Always return the same message to prevent email enumeration
        $message = __('auth.reset_link_sent');

        if (!$user) {
            return back()->with('status', $message);
        }

        // Delete old tokens for this email
        DB::table('password_reset_tokens')
            ->where('email', $request->email)
            ->delete();

        // Generate new token
        $token = Str::random(64);

        // Store token in database
        DB::table('password_reset_tokens')->insert([
            'email' => $request->email,
            'token' => Hash::make($token),
            'created_at' => Carbon::now(),
        ]);

        // Send email with reset link
        try {
            Mail::to($user->email)->send(new ResetPasswordMail($user, $token));
        } catch (\Exception $e) {
            \Log::error('Failed to send password reset email: ' . $e->getMessage());
            return back()->with('error', __('auth.reset_email_failed'));
        }

        return back()->with('status', $message);
    }

    /**
     * Show the reset password form
     */
    public function showResetPasswordForm(Request $request, $token)
    {
        $email = $request->email;
        
        // Verify token exists and is not expired (60 minutes)
        $tokenData = DB::table('password_reset_tokens')
            ->where('email', $email)
            ->first();

        if (!$tokenData) {
            return redirect()->route('login')
                ->with('error', __('auth.invalid_reset_token'));
        }

        // Check if token is expired (60 minutes)
        $createdAt = Carbon::parse($tokenData->created_at);
        if ($createdAt->addMinutes(60)->isPast()) {
            DB::table('password_reset_tokens')->where('email', $email)->delete();
            return redirect()->route('login')
                ->with('error', __('auth.expired_reset_token'));
        }

        return view('auth.reset-password', [
            'token' => $token,
            'email' => $email,
        ]);
    }

    /**
     * Reset the password
     */
    public function resetPassword(Request $request)
    {
        $request->validate([
            'email' => 'required|email',
            'password' => 'required|string|min:6|confirmed',
            'token' => 'required',
        ]);

        // Get token data
        $tokenData = DB::table('password_reset_tokens')
            ->where('email', $request->email)
            ->first();

        if (!$tokenData) {
            return back()->with('error', __('auth.invalid_reset_token'));
        }

        // Verify token
        if (!Hash::check($request->token, $tokenData->token)) {
            return back()->with('error', __('auth.invalid_reset_token'));
        }

        // Check if token is expired (60 minutes)
        $createdAt = Carbon::parse($tokenData->created_at);
        if ($createdAt->addMinutes(60)->isPast()) {
            DB::table('password_reset_tokens')->where('email', $request->email)->delete();
            return back()->with('error', __('auth.expired_reset_token'));
        }

        // Find user and update password
        $user = User::where('email', $request->email)->first();

        if (!$user) {
            return back()->with('error', __('auth.user_not_found'));
        }

        // Update password
        $user->update([
            'Password' => Hash::make($request->password),
        ]);

        // Delete used token
        DB::table('password_reset_tokens')->where('email', $request->email)->delete();

        // Log the password reset
        \Log::info('Password reset successful for user: ' . $user->Username);

        return redirect()->route('login')
            ->with('success', __('auth.password_reset_success'));
    }
}

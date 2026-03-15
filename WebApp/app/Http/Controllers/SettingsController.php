<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Facades\Config;
use App\Mail\TrainingCompletedMail;
use App\Models\EmailSetting;

class SettingsController extends Controller
{
    /**
     * Hiển thị trang cấu hình email
     */
    public function emailSettings()
    {
        $smtpSettings = EmailSetting::getByGroup('smtp');
        $notificationSettings = EmailSetting::getByGroup('notification');
        
        return view('admin.settings.email', compact('smtpSettings', 'notificationSettings'));
    }

    /**
     * Cập nhật email settings
     */
    public function updateEmail(Request $request)
    {
        $request->validate([
            'notification_email' => 'required|email|max:255',
            'smtp_host' => 'required|string|max:255',
            'smtp_port' => 'required|integer|min:1|max:65535',
            'smtp_username' => 'required|email|max:255',
            'smtp_password' => 'nullable|string|max:255',
            'smtp_encryption' => 'required|in:tls,ssl',
            'mail_from_address' => 'required|email|max:255',
            'mail_from_name' => 'required|string|max:255',
        ]);

        try {
            // Update all settings
            EmailSetting::set('notification_email', $request->notification_email);
            EmailSetting::set('smtp_host', $request->smtp_host);
            EmailSetting::set('smtp_port', $request->smtp_port);
            EmailSetting::set('smtp_username', $request->smtp_username);
            
            // Only update password if provided
            if ($request->filled('smtp_password')) {
                EmailSetting::set('smtp_password', $request->smtp_password);
            }
            
            EmailSetting::set('smtp_encryption', $request->smtp_encryption);
            EmailSetting::set('mail_from_address', $request->mail_from_address);
            EmailSetting::set('mail_from_name', $request->mail_from_name);

            // Apply settings to current config
            $this->applyEmailConfig();

            return redirect()->route('admin.settings.email')
                ->with('success', 'Email settings updated successfully!');
                
        } catch (\Exception $e) {
            return redirect()->route('admin.settings.email')
                ->with('error', 'Failed to update settings: ' . $e->getMessage());
        }
    }

    /**
     * Apply email settings from database to config
     */
    private function applyEmailConfig()
    {
        $settings = EmailSetting::getAllAsArray();

        if (isset($settings['smtp_host'])) {
            Config::set('mail.mailers.smtp.host', $settings['smtp_host']);
        }
        if (isset($settings['smtp_port'])) {
            Config::set('mail.mailers.smtp.port', $settings['smtp_port']);
        }
        if (isset($settings['smtp_username'])) {
            Config::set('mail.mailers.smtp.username', $settings['smtp_username']);
        }
        if (isset($settings['smtp_password'])) {
            Config::set('mail.mailers.smtp.password', $settings['smtp_password']);
        }
        if (isset($settings['smtp_encryption'])) {
            Config::set('mail.mailers.smtp.encryption', $settings['smtp_encryption']);
        }
        if (isset($settings['mail_from_address'])) {
            Config::set('mail.from.address', $settings['mail_from_address']);
        }
        if (isset($settings['mail_from_name'])) {
            Config::set('mail.from.name', $settings['mail_from_name']);
        }
    }

    /**
     * Gửi test email
     */
    public function sendTestEmail()
    {
        try {
            // Apply current settings
            $this->applyEmailConfig();

            $notificationEmail = EmailSetting::get('notification_email');

            if (!$notificationEmail) {
                return redirect()->route('admin.settings.email')
                    ->with('error', 'Please set notification email address first.');
            }

            // Tạo dữ liệu test
            $trainingData = [
                'model_type' => 'random_forest',
                'dataset_path' => 'test/dataset.csv',
                'model_name' => 'Test_Model',
                'test_size' => 0.2,
                'dataset_name' => 'Test Dataset',
            ];

            $result = [
                'success' => true,
                'message' => 'This is a test email',
                'data' => [
                    'metrics' => [
                        'r2_score' => 0.9234,
                        'rmse' => 0.1456,
                        'mae' => 0.1123,
                        'mse' => 0.0212,
                    ],
                    'mlflow_info' => [
                        'run_id' => 'test_run_' . time(),
                        'experiment_id' => '0',
                        'model_uri' => 'runs:/test_run_' . time() . '/model',
                    ]
                ]
            ];

            Mail::to($notificationEmail)->send(new TrainingCompletedMail($trainingData, $result));
            
            return redirect()->route('admin.settings.email')
                ->with('success', 'Test email sent successfully to ' . $notificationEmail . '! Check your inbox.');
                
        } catch (\Exception $e) {
            return redirect()->route('admin.settings.email')
                ->with('error', 'Failed to send test email: ' . $e->getMessage());
        }
    }
}

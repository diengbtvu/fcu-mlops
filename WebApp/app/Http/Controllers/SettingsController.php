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
    private const GROQ_KEYS_SETTING = 'groq_api_keys';

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
     * Hiển thị trang cấu hình AI API keys
     */
    public function aiSettings()
    {
        $groqKeys = $this->normalizeGroqKeys(EmailSetting::get(self::GROQ_KEYS_SETTING, ''));
        $maskedGroqKeys = [];
        foreach ($groqKeys as $index => $key) {
            $maskedGroqKeys[] = [
                'index' => $index,
                'label' => $this->maskApiKey($key),
            ];
        }

        return view('admin.settings.ai', [
            'groqKeyCount' => count($groqKeys),
            'maskedGroqKeys' => $maskedGroqKeys,
        ]);
    }

    /**
     * Cập nhật AI API keys
     */
    public function updateAi(Request $request)
    {
        $request->validate([
            'groq_api_keys' => 'nullable|string|max:20000',
            'clear_groq_api_keys' => 'nullable|boolean',
            'delete_groq_key_index' => 'nullable|integer|min:0',
        ]);

        try {
            $existingKeys = $this->normalizeGroqKeys(EmailSetting::get(self::GROQ_KEYS_SETTING, ''));

            if ($request->boolean('clear_groq_api_keys')) {
                $groqKeys = [];
            } elseif ($request->filled('delete_groq_key_index')) {
                $deleteIndex = (int) $request->input('delete_groq_key_index');
                if (array_key_exists($deleteIndex, $existingKeys)) {
                    unset($existingKeys[$deleteIndex]);
                }
                $groqKeys = array_values($existingKeys);
            } elseif ($request->filled('groq_api_keys')) {
                $newKeys = $this->normalizeGroqKeys($request->input('groq_api_keys'));
                $groqKeys = $this->mergeGroqKeys($existingKeys, $newKeys);
            } else {
                $groqKeys = $existingKeys;
            }

            EmailSetting::set(
                self::GROQ_KEYS_SETTING,
                implode("\n", $groqKeys),
                [
                    'type' => 'textarea',
                    'group' => 'ai',
                    'description' => 'Groq API key pool used by report explanations and benchmark evaluation',
                    'is_encrypted' => true,
                ]
            );

            $message = $request->filled('delete_groq_key_index')
                ? 'Groq API key removed.'
                : 'AI API key settings updated successfully.';

            return redirect()->route('admin.settings.ai')->with('success', $message);
        } catch (\Exception $e) {
            return redirect()->route('admin.settings.ai')
                ->with('error', 'Failed to update AI API keys: ' . $e->getMessage());
        }
    }

    private function normalizeGroqKeys(?string $rawValue): array
    {
        $items = preg_split('/[\s,;]+/', (string) $rawValue) ?: [];
        $keys = [];
        foreach ($items as $item) {
            $key = trim((string) $item);
            if ($key === '' || in_array($key, $keys, true)) {
                continue;
            }
            $keys[] = $key;
        }
        return $keys;
    }

    private function mergeGroqKeys(array $existingKeys, array $newKeys): array
    {
        $keys = [];
        foreach (array_merge($existingKeys, $newKeys) as $key) {
            $key = trim((string) $key);
            if ($key === '' || in_array($key, $keys, true)) {
                continue;
            }
            $keys[] = $key;
        }
        return $keys;
    }

    private function maskApiKey(string $key): string
    {
        $key = trim($key);
        if ($key === '') {
            return '';
        }
        $prefix = substr($key, 0, min(7, strlen($key)));
        $suffix = strlen($key) > 4 ? substr($key, -4) : '';
        return $suffix !== '' ? $prefix . '...' . $suffix : $prefix . '...';
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

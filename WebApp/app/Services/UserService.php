<?php

namespace App\Services;

use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class UserService
{
    /**
     * Generate unique UserCode with format: USR + 7 random digits
     * 
     * @return string
     */
    public function generateUniqueUserCode(): string
    {
        do {
            // Generate 7 random digits
            $randomNumber = mt_rand(1, 9999999);
            
            // Pad with zeros to ensure 7 digits
            $paddedNumber = str_pad($randomNumber, 7, '0', STR_PAD_LEFT);
            
            // Create UserCode with USR prefix
            $userCode = 'USR' . $paddedNumber;
            
            // Check if this UserCode already exists
            $exists = User::where('UserCode', $userCode)->exists();
            
        } while ($exists);
        
        return $userCode;
    }

    /**
     * Create a new user with auto-generated UserCode
     * 
     * @param array $userData
     * @return User
     */
    public function createUser(array $userData): User
    {
        // Generate unique UserCode if not provided
        if (!isset($userData['UserCode']) || empty($userData['UserCode'])) {
            $userData['UserCode'] = $this->generateUniqueUserCode();
        }

        // Hash password if provided
        if (isset($userData['Password'])) {
            $userData['Password'] = Hash::make($userData['Password']);
        }

        // Set default role to user (role_id = 2) if not specified
        if (!isset($userData['role_id'])) {
            $userData['role_id'] = 2;
        }

        return User::create($userData);
    }

    /**
     * Update user data
     * 
     * @param User $user
     * @param array $userData
     * @return bool
     */
    public function updateUser(User $user, array $userData): bool
    {
        // Don't allow downgrading the primary admin account (UserCode: AD00000000)
        if ($user->UserCode === 'AD00000000' && isset($userData['role_id']) && $userData['role_id'] != 1) {
            return false;
        }

        // Don't allow updating admin users' basic info if current user is also admin trying to edit themselves
        if ($user->role_id === 1 && auth()->id() === $user->id && isset($userData['role_id']) && $userData['role_id'] != 1) {
            return false;
        }

        // Remove password from update data if not provided
        if (isset($userData['Password']) && empty($userData['Password'])) {
            unset($userData['Password']);
        } elseif (isset($userData['Password'])) {
            $userData['Password'] = Hash::make($userData['Password']);
        }

        return $user->update($userData);
    }

    /**
     * Reset user password
     * 
     * @param User $user
     * @param string $newPassword
     * @return bool
     */
    public function resetPassword(User $user, string $newPassword = null): bool
    {
        // Don't allow resetting admin password
        if ($user->role_id === 1) {
            return false;
        }

        // Generate random password if not provided
        if (!$newPassword) {
            $newPassword = $this->generateRandomPassword();
        }

        return $user->update([
            'Password' => Hash::make($newPassword)
        ]);
    }

    /**
     * Generate random password
     * 
     * @param int $length
     * @return string
     */
    private function generateRandomPassword(int $length = 8): string
    {
        $uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        $lowercase = 'abcdefghijklmnopqrstuvwxyz';
        $numbers = '0123456789';
        $symbols = '!@#$%^&*';

        // Ensure at least one character from each category
        $password = '';
        $password .= $uppercase[mt_rand(0, strlen($uppercase) - 1)];
        $password .= $lowercase[mt_rand(0, strlen($lowercase) - 1)];
        $password .= $numbers[mt_rand(0, strlen($numbers) - 1)];
        $password .= $symbols[mt_rand(0, strlen($symbols) - 1)];

        // Fill the rest randomly
        $allChars = $uppercase . $lowercase . $numbers . $symbols;
        for ($i = 4; $i < $length; $i++) {
            $password .= $allChars[mt_rand(0, strlen($allChars) - 1)];
        }

        // Shuffle the password
        return str_shuffle($password);
    }

    /**
     * Anonymize user data (for GDPR compliance)
     * 
     * @param User $user
     * @return bool
     */
    public function anonymizeUser(User $user): bool
    {
        // Don't allow anonymizing admin users
        if ($user->role_id === 1) {
            return false;
        }

        return $user->update([
            'FullName' => 'Anonymous User',
            'BirthDate' => '1900-01-01',
            'Address' => 'N/A',
            'Username' => 'anon_' . $user->UserCode,
        ]);
    }

    /**
     * Delete user and associated data
     * 
     * @param User $user
     * @param bool $forceDelete
     * @return bool
     */
    public function deleteUser(User $user, bool $forceDelete = false): bool
    {
        // Don't allow deleting admin users
        if ($user->role_id === 1) {
            return false;
        }

        // Check if user has predictions
        $predictionCount = $user->predictions()->count();
        
        if ($predictionCount > 0 && !$forceDelete) {
            // Don't delete if user has predictions and not forced
            return false;
        }

        // Delete associated predictions if force delete
        if ($forceDelete) {
            $user->predictions()->delete();
        }

        return $user->delete();
    }

    /**
     * Get user statistics
     * 
     * @param User $user
     * @return array
     */
    public function getUserStatistics(User $user): array
    {
        $avgHpr = $user->predictions()->avg('HPR') ?? 0;

        return [
            'total_predictions' => $user->predictions()->count(),
            'recent_predictions' => $user->predictions()
                ->where('created_at', '>=', now()->subDays(30))
                ->count(),
            'avg_hpr' => $avgHpr,
            'last_prediction' => $user->predictions()
                ->latest()
                ->first()?->created_at,
        ];
    }
}

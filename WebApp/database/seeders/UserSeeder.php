<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\User;
use App\Services\UserService;

class UserSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $userService = new UserService();

        // Create Administrator (special UserCode for admin)
        User::create([
            'UserCode' => 'AD00000000', // Special UserCode for admin
            'FullName' => 'System Administrator',
            'Gender' => 'Male',
            'BirthDate' => '1985-01-01',
            'Address' => '123 Admin Street, System City',
            'Username' => 'admin',
            'email' => 'admin@hydrogen-mlops.local',
            'Password' => bcrypt('Admin@123'),
            'role_id' => 1,
        ]);
        User::create([
            'UserCode' => 'USR0000000', // Special UserCode for admin
            'FullName' => 'Test User',
            'Gender' => 'Male',
            'BirthDate' => '1990-01-01',
            'Address' => '123 Test Street, Test City',
            'Username' => 'testuser',
            'Password' => bcrypt('Test@123'),
            'role_id' => 2,
        ]);

        // Create Test Users with auto-generated UserCodes
        $testUsers = [
            [
                'FullName' => 'Dr. John Smith',
                'Gender' => 'Male',
                'BirthDate' => '1990-03-15',
                'Address' => '456 Research Avenue, Science City',
                'Username' => 'johnsmith',
                'Password' => 'User@123',
            ],
            [
                'FullName' => 'Dr. Jane Wilson',
                'Gender' => 'Female',
                'BirthDate' => '1988-07-22',
                'Address' => '789 Laboratory Street, Bio Town',
                'Username' => 'janewilson',
                'Password' => 'User@123',
            ],
            [
                'FullName' => 'Prof. Michael Brown',
                'Gender' => 'Male',
                'BirthDate' => '1975-11-08',
                'Address' => '321 University Drive, Academic City',
                'Username' => 'mikebrown',
                'Password' => 'User@123',
            ],
            [
                'FullName' => 'Dr. Sarah Davis',
                'Gender' => 'Female',
                'BirthDate' => '1992-05-12',
                'Address' => '654 Medical Center, Health District',
                'Username' => 'sarahdavis',
                'Password' => 'User@123',
            ],
        ];

        // Create users using UserService for auto-generated UserCodes
        foreach ($testUsers as $userData) {
            $userService->createUser($userData);
        }
    }
}

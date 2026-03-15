<?php

namespace Tests\Unit;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use App\Models\MLModel;
use App\Models\Prediction;
use App\Services\UserService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;

class UserServiceTest extends TestCase
{
    use RefreshDatabase;

    protected $userService;

    protected function setUp(): void
    {
        parent::setUp();
        
        $this->userService = new UserService();
        
        // Create roles
        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_generates_unique_user_code()
    {
        $userCode = $this->userService->generateUniqueUserCode();
        
        $this->assertStringStartsWith('USR', $userCode);
        $this->assertEquals(10, strlen($userCode)); // USR + 7 digits
        $this->assertMatchesRegularExpression('/^USR\d{7}$/', $userCode);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_generates_different_user_codes()
    {
        $userCode1 = $this->userService->generateUniqueUserCode();
        $userCode2 = $this->userService->generateUniqueUserCode();
        
        $this->assertNotEquals($userCode1, $userCode2);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_avoids_duplicate_user_codes()
    {
        // Create a user with a specific UserCode
        User::factory()->create(['UserCode' => 'USR1234567']);
        
        // Generate codes until we get a different one
        $attempts = 0;
        $maxAttempts = 100; // Prevent infinite loop in test
        
        do {
            $newCode = $this->userService->generateUniqueUserCode();
            $attempts++;
        } while ($newCode === 'USR1234567' && $attempts < $maxAttempts);
        
        $this->assertNotEquals('USR1234567', $newCode);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_creates_user_with_auto_generated_user_code()
    {
        $userData = [
            'FullName' => 'Test User',
            'Gender' => 'Male',
            'BirthDate' => '1990-01-01',
            'Address' => 'Test Address',
            'Username' => 'testuser',
            'Password' => 'password123'
        ];

        $user = $this->userService->createUser($userData);

        $this->assertInstanceOf(User::class, $user);
        $this->assertStringStartsWith('USR', $user->UserCode);
        $this->assertEquals('Test User', $user->FullName);
        $this->assertEquals('testuser', $user->Username);
        $this->assertEquals(2, $user->role_id); // Default user role
        $this->assertTrue(Hash::check('password123', $user->Password));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_creates_user_with_provided_user_code()
    {
        $userData = [
            'UserCode' => 'USR9999999',
            'FullName' => 'Test User',
            'Gender' => 'Male',
            'BirthDate' => '1990-01-01',
            'Address' => 'Test Address',
            'Username' => 'testuser',
            'Password' => 'password123'
        ];

        $user = $this->userService->createUser($userData);

        $this->assertEquals('USR9999999', $user->UserCode);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_creates_user_with_custom_role()
    {
        $userData = [
            'FullName' => 'Admin User',
            'Gender' => 'Female',
            'BirthDate' => '1985-05-15',
            'Address' => 'Admin Address',
            'Username' => 'adminuser',
            'Password' => 'admin123',
            'role_id' => 1
        ];

        $user = $this->userService->createUser($userData);

        $this->assertEquals(1, $user->role_id); // Admin role
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_updates_user_data()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $updateData = [
            'FullName' => 'Updated Name',
            'Gender' => 'Female',
            'BirthDate' => '1995-12-25',
            'Address' => 'Updated Address',
            'Username' => 'updateduser'
        ];

        $result = $this->userService->updateUser($user, $updateData);

        $this->assertTrue($result);
        $user->refresh();
        $this->assertEquals('Updated Name', $user->FullName);
        $this->assertEquals('updateduser', $user->Username);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_cannot_downgrade_primary_admin_user()
    {
        $adminUser = User::factory()->create([
            'role_id' => 1,
            'UserCode' => 'AD00000000',
        ]);
        
        $updateData = [
            'FullName' => 'Should Not Update',
            'role_id' => 2,
        ];

        $result = $this->userService->updateUser($adminUser, $updateData);

        $this->assertFalse($result);
        $adminUser->refresh();
        $this->assertEquals(1, $adminUser->role_id);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_resets_user_password()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $originalPassword = $user->Password;

        $result = $this->userService->resetPassword($user);

        $this->assertTrue($result);
        $user->refresh();
        $this->assertNotEquals($originalPassword, $user->Password);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_resets_password_with_custom_password()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $customPassword = 'custompass123';

        $result = $this->userService->resetPassword($user, $customPassword);

        $this->assertTrue($result);
        $user->refresh();
        $this->assertTrue(Hash::check($customPassword, $user->Password));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_cannot_reset_admin_password()
    {
        $adminUser = User::factory()->create(['role_id' => 1]);
        $originalPassword = $adminUser->Password;

        $result = $this->userService->resetPassword($adminUser);

        $this->assertFalse($result);
        $adminUser->refresh();
        $this->assertEquals($originalPassword, $adminUser->Password);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_anonymizes_user_data()
    {
        $user = User::factory()->create([
            'role_id' => 2,
            'FullName' => 'Original Name',
            'BirthDate' => '1990-05-15',
            'Address' => 'Original Address',
            'Username' => 'originaluser'
        ]);

        $result = $this->userService->anonymizeUser($user);

        $this->assertTrue($result);
        $user->refresh();
        $this->assertEquals('Anonymous User', $user->FullName);
        $this->assertEquals('1900-01-01', $user->BirthDate->format('Y-m-d'));
        $this->assertEquals('N/A', $user->Address);
        $this->assertStringStartsWith('anon_', $user->Username);
        $this->assertStringContainsString($user->UserCode, $user->Username);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_cannot_anonymize_admin_user()
    {
        $adminUser = User::factory()->create([
            'role_id' => 1,
            'FullName' => 'Admin Name'
        ]);
        $originalData = $adminUser->toArray();

        $result = $this->userService->anonymizeUser($adminUser);

        $this->assertFalse($result);
        $adminUser->refresh();
        $this->assertEquals('Admin Name', $adminUser->FullName);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_deletes_user_without_predictions()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $userId = $user->id;

        $result = $this->userService->deleteUser($user);

        $this->assertTrue($result);
        $this->assertDatabaseMissing('users', ['id' => $userId]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_cannot_delete_user_with_predictions()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $model = MLModel::factory()->create();
        Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
        ]);

        $result = $this->userService->deleteUser($user);

        $this->assertFalse($result);
        $this->assertDatabaseHas('users', ['id' => $user->id]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_force_delete_user_with_predictions()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $userId = $user->id;

        $result = $this->userService->deleteUser($user, true);

        $this->assertTrue($result);
        $this->assertDatabaseMissing('users', ['id' => $userId]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_cannot_delete_admin_user()
    {
        $adminUser = User::factory()->create(['role_id' => 1]);

        $result = $this->userService->deleteUser($adminUser);

        $this->assertFalse($result);
        $this->assertDatabaseHas('users', ['id' => $adminUser->id]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_gets_user_statistics()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $statistics = $this->userService->getUserStatistics($user);

        $this->assertArrayHasKey('total_predictions', $statistics);
        $this->assertArrayHasKey('recent_predictions', $statistics);
        $this->assertArrayHasKey('avg_hpr', $statistics);
        $this->assertArrayHasKey('last_prediction', $statistics);
        $this->assertEquals(0, $statistics['total_predictions']);
        $this->assertEquals(0, $statistics['recent_predictions']);
        $this->assertEquals(0, $statistics['avg_hpr']);
        $this->assertNull($statistics['last_prediction']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function generated_password_meets_requirements()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        // Use reflection to access the private method
        $reflection = new \ReflectionClass($this->userService);
        $method = $reflection->getMethod('generateRandomPassword');
        $method->setAccessible(true);
        
        $password = $method->invoke($this->userService);
        
        $this->assertGreaterThanOrEqual(8, strlen($password));
        $this->assertMatchesRegularExpression('/[A-Z]/', $password); // Has uppercase
        $this->assertMatchesRegularExpression('/[a-z]/', $password); // Has lowercase
        $this->assertMatchesRegularExpression('/[0-9]/', $password); // Has numbers
        $this->assertMatchesRegularExpression('/[!@#$%^&*]/', $password); // Has symbols
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function generated_password_has_custom_length()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        // Use reflection to access the private method
        $reflection = new \ReflectionClass($this->userService);
        $method = $reflection->getMethod('generateRandomPassword');
        $method->setAccessible(true);
        
        $password = $method->invoke($this->userService, 12); // Custom length
        
        $this->assertEquals(12, strlen($password));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_handles_empty_password_in_update()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $originalPassword = $user->Password;
        
        $updateData = [
            'FullName' => 'Updated Name',
            'Password' => '' // Empty password should be ignored
        ];

        $result = $this->userService->updateUser($user, $updateData);

        $this->assertTrue($result);
        $user->refresh();
        $this->assertEquals('Updated Name', $user->FullName);
        $this->assertEquals($originalPassword, $user->Password); // Password unchanged
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_hashes_password_in_update()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $updateData = [
            'FullName' => 'Updated Name',
            'Password' => 'newpassword123'
        ];

        $result = $this->userService->updateUser($user, $updateData);

        $this->assertTrue($result);
        $user->refresh();
        $this->assertTrue(Hash::check('newpassword123', $user->Password));
    }
}

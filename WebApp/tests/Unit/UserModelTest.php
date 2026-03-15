<?php

namespace Tests\Unit;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use App\Models\Prediction;
use App\Models\MLModel;
use Illuminate\Foundation\Testing\RefreshDatabase;

class UserModelTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Create roles
        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_has_fillable_attributes()
    {
        $fillable = [
            'UserCode',
            'FullName',
            'Gender',
            'BirthDate',
            'Address',
            'Username',
            'email',
            'Password',
            'role_id',
            'language',
        ];

        $user = new User();
        
        $this->assertEquals($fillable, $user->getFillable());
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_hides_sensitive_attributes()
    {
        $hidden = [
            'Password',
            'remember_token',
        ];

        $user = new User();
        
        $this->assertEquals($hidden, $user->getHidden());
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_casts_password_as_hashed()
    {
        $user = new User();
        $casts = $user->getCasts();
        
        $this->assertArrayHasKey('Password', $casts);
        $this->assertEquals('hashed', $casts['Password']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_uses_password_field_for_authentication()
    {
        $user = User::factory()->create(['Password' => 'hashedpassword']);
        
        $this->assertNotEquals('hashedpassword', $user->getAuthPassword());
        $this->assertTrue(\Hash::check('hashedpassword', $user->getAuthPassword()));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_belongs_to_a_role()
    {
        $role = Role::first();
        $user = User::factory()->create(['role_id' => $role->id]);
        
        $this->assertInstanceOf(Role::class, $user->role);
        $this->assertEquals($role->id, $user->role->id);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_has_many_predictions()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();
        
        $prediction1 = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id
        ]);
        $prediction2 = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id
        ]);
        
        $this->assertCount(2, $user->predictions);
        $this->assertContains($prediction1->id, $user->predictions->pluck('id'));
        $this->assertContains($prediction2->id, $user->predictions->pluck('id'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_created_with_factory()
    {
        $user = User::factory()->create([
            'FullName' => 'Test User',
            'Username' => 'testuser123',
            'role_id' => 2
        ]);

        $this->assertDatabaseHas('users', [
            'FullName' => 'Test User',
            'Username' => 'testuser123',
            'role_id' => 2
        ]);
        
        $this->assertNotEmpty($user->UserCode);
        $this->assertNotEmpty($user->Password);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_code_is_unique()
    {
        $user1 = User::factory()->create();
        $user2 = User::factory()->create();
        
        $this->assertNotEquals($user1->UserCode, $user2->UserCode);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_has_valid_gender_options()
    {
        $maleUser = User::factory()->create(['Gender' => 'Male']);
        $femaleUser = User::factory()->create(['Gender' => 'Female']);
        
        $this->assertEquals('Male', $maleUser->Gender);
        $this->assertEquals('Female', $femaleUser->Gender);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function birth_date_is_cast_to_date()
    {
        $user = User::factory()->create(['BirthDate' => '1990-05-15']);
        
        $this->assertInstanceOf(\Carbon\Carbon::class, $user->BirthDate);
        $this->assertEquals('1990-05-15', $user->BirthDate->format('Y-m-d'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function password_is_automatically_hashed()
    {
        $user = User::factory()->create(['Password' => 'plainpassword']);
        
        $this->assertNotEquals('plainpassword', $user->getAttributes()['Password']);
        $this->assertTrue(\Hash::check('plainpassword', $user->Password));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_serialized_to_array_without_sensitive_data()
    {
        $user = User::factory()->create([
            'FullName' => 'Test User',
            'Username' => 'testuser',
            'Password' => 'password123'
        ]);
        
        $userArray = $user->toArray();
        
        $this->assertArrayHasKey('FullName', $userArray);
        $this->assertArrayHasKey('Username', $userArray);
        $this->assertArrayNotHasKey('Password', $userArray);
        $this->assertArrayNotHasKey('remember_token', $userArray);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_serialized_to_json_without_sensitive_data()
    {
        $user = User::factory()->create([
            'FullName' => 'Test User',
            'Username' => 'testuser',
            'Password' => 'password123'
        ]);
        
        $userJson = json_decode($user->toJson(), true);
        
        $this->assertArrayHasKey('FullName', $userJson);
        $this->assertArrayHasKey('Username', $userJson);
        $this->assertArrayNotHasKey('Password', $userJson);
        $this->assertArrayNotHasKey('remember_token', $userJson);
    }
}

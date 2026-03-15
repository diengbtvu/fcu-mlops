<?php

namespace App\Models;

use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Notifications\Notifiable;

class User extends Authenticatable
{
    use HasFactory, Notifiable;

    protected $fillable = [
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

    protected $hidden = [
        'Password',
        'remember_token',
    ];

    protected function casts(): array
    {
        return [
            'BirthDate' => 'date',
            'Password' => 'hashed',
        ];
    }

    public function getAuthPassword()
    {
        return $this->Password;
    }

    public function role()
    {
        return $this->belongsTo(Role::class);
    }

    /**
     * Many-to-many relationship with roles (a user can have multiple permission groups)
     */
    public function roles()
    {
        return $this->belongsToMany(Role::class, 'user_roles')
                    ->withTimestamps();
    }

    public function predictions()
    {
        return $this->hasMany(Prediction::class);
    }

    public function datasets()
    {
        return $this->hasMany(Dataset::class, 'UploadedBy', 'id');
    }

    public function trainedModels()
    {
        return $this->hasMany(MLModel::class, 'TrainedBy', 'id');
    }

    /**
     * User-specific permissions (overrides role permissions)
     */
    public function userPermissions()
    {
        return $this->belongsToMany(Permission::class, 'user_permissions')
                    ->withPivot('granted')
                    ->withTimestamps();
    }

    /**
     * Check if user has a specific permission.
     * Priority: User-specific permission > Any role permission
     * Admin role (role_id = 1) always has all permissions.
     */
    public function hasPermission($permissionName)
    {
        // Admin always has all permissions
        if ($this->role_id === 1) {
            return true;
        }
        
        // Check if user has a specific override for this permission
        $userPermission = $this->userPermissions()->where('name', $permissionName)->first();
        if ($userPermission) {
            // Return the override value (granted = true/false)
            return $userPermission->pivot->granted;
        }
        
        // Check permissions from all assigned roles
        foreach ($this->roles as $role) {
            if ($role->hasPermission($permissionName)) {
                return true;
            }
        }
        
        // Fall back to default role permissions (if exists)
        return $this->role && $this->role->hasPermission($permissionName);
    }

    /**
     * Check if user has any of the given permissions.
     * Admin role (role_id = 1) always has all permissions.
     */
    public function hasAnyPermission(array $permissions)
    {
        // Admin always has all permissions
        if ($this->role_id === 1) {
            return true;
        }
        
        foreach ($permissions as $permission) {
            if ($this->hasPermission($permission)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Check if user has all of the given permissions.
     * Admin role (role_id = 1) always has all permissions.
     */
    public function hasAllPermissions(array $permissions)
    {
        // Admin always has all permissions
        if ($this->role_id === 1) {
            return true;
        }
        
        foreach ($permissions as $permission) {
            if (!$this->hasPermission($permission)) {
                return false;
            }
        }
        return true;
    }
}

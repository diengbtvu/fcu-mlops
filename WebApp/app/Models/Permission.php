<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Permission extends Model
{
    use HasFactory;

    protected $fillable = ['name', 'description'];

    /**
     * The roles that belong to the permission.
     */
    public function roles()
    {
        return $this->belongsToMany(Role::class, 'role_permission');
    }

    /**
     * The users that have this permission directly assigned.
     */
    public function users()
    {
        return $this->belongsToMany(User::class, 'user_permissions')
                    ->withPivot('granted')
                    ->withTimestamps();
    }
}

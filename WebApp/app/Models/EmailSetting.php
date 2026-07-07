<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Crypt;

class EmailSetting extends Model
{
    protected $fillable = [
        'key',
        'value',
        'type',
        'group',
        'description',
        'is_encrypted',
    ];

    protected $casts = [
        'is_encrypted' => 'boolean',
    ];

    /**
     * Get decrypted value
     */
    public function getValueAttribute($value)
    {
        if ($this->is_encrypted && $value) {
            try {
                return Crypt::decryptString($value);
            } catch (\Exception $e) {
                return null;
            }
        }
        return $value;
    }

    /**
     * Set encrypted value
     */
    public function setValueAttribute($value)
    {
        if ($this->is_encrypted && $value) {
            $this->attributes['value'] = Crypt::encryptString($value);
        } else {
            $this->attributes['value'] = $value;
        }
    }

    /**
     * Get setting value by key
     */
    public static function get($key, $default = null)
    {
        $setting = static::where('key', $key)->first();
        return $setting ? $setting->value : $default;
    }

    /**
     * Set setting value by key
     */
    public static function set($key, $value, array $attributes = [])
    {
        $setting = static::where('key', $key)->first();
        
        if ($setting) {
            foreach ($attributes as $attribute => $attributeValue) {
                if ($attribute !== 'key') {
                    $setting->{$attribute} = $attributeValue;
                }
            }
            $setting->value = $value;
            $setting->save();
        } else {
            $setting = new static(array_merge(['key' => $key], $attributes));
            $setting->value = $value;
            $setting->save();
        }
        
        return true;
    }

    /**
     * Get all settings as key-value array
     */
    public static function getAllAsArray()
    {
        return static::all()->pluck('value', 'key')->toArray();
    }

    /**
     * Get settings by group
     */
    public static function getByGroup($group)
    {
        return static::where('group', $group)->get();
    }
}

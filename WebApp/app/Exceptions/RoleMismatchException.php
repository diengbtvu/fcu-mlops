<?php

namespace App\Exceptions;

use Exception;

class RoleMismatchException extends Exception
{
    protected $currentRole;
    protected $requiredRole;

    public function __construct($currentRole, $requiredRole, $message = 'Role permission mismatch')
    {
        $this->currentRole = $currentRole;
        $this->requiredRole = $requiredRole;
        
        parent::__construct($message);
    }

    public function getCurrentRole()
    {
        return $this->currentRole;
    }

    public function getRequiredRole()
    {
        return $this->requiredRole;
    }
}

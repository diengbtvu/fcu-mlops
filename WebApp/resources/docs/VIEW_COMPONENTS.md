# View Components Documentation

## Overview
This document describes the modular view components created for the Hydrogen Production Rate (HPR) prediction system. These components follow Laravel's Blade component architecture to provide reusable, maintainable UI elements.

## Component Categories

### 1. Layout Components (`components/layout/`)

#### Header Component
**Path:** `components/layout/header.blade.php`
**Usage:** `<x-layout.header />`
**Description:** Main navigation header with user menu and logout functionality.

#### Sidebar Component  
**Path:** `components/layout/sidebar.blade.php`
**Usage:** `<x-layout.sidebar />`
**Description:** Main sidebar container with brand logo and navigation menu.

#### Content Header Component
**Path:** `components/layout/content-header.blade.php`
**Usage:** `<x-layout.content-header title="Page Title" :breadcrumbs="$breadcrumbs" />`
**Props:**
- `title` (string): Page title
- `breadcrumbs` (array): Breadcrumb navigation items

#### Footer Component
**Path:** `components/layout/footer.blade.php` 
**Usage:** `<x-layout.footer year="2025" company="Your Company" />`
**Props:**
- `year` (string): Copyright year (defaults to current year)
- `company` (string): Company name

### 2. UI Components (`components/ui/`)

#### Alert Component
**Path:** `components/ui/alert.blade.php`
**Usage:** `<x-ui.alert type="success" dismissible>Message content</x-ui.alert>`
**Props:**
- `type` (string): Alert type (success, error, warning, info, etc.)
- `dismissible` (boolean): Whether alert can be dismissed
- `icon` (string): Custom icon class

#### Session Messages Component
**Path:** `components/ui/session-messages.blade.php`
**Usage:** `<x-ui.session-messages />`
**Description:** Automatically displays all session flash messages and validation errors.

#### Small Box Component
**Path:** `components/ui/small-box.blade.php`
**Usage:** 
```blade
<x-ui.small-box 
    color="info" 
    value="123" 
    label="Total Users" 
    icon="bi bi-people" 
    :link="route('users.index')" 
    linkText="View Users" />
```
**Props:**
- `color` (string): Box color theme
- `value` (string): Main display value
- `label` (string): Description label
- `icon` (string): Icon class
- `link` (string): Optional footer link URL
- `linkText` (string): Footer link text

#### Data Table Component
**Path:** `components/ui/data-table.blade.php`
**Usage:**
```blade
<x-ui.data-table 
    :headers="['Name', 'Email', 'Actions']"
    id="usersTable"
    title="Users List">
    {{-- Table rows go here --}}
</x-ui.data-table>
```
**Props:**
- `headers` (array): Table column headers
- `id` (string): Table HTML ID
- `title` (string): Card title
- `responsive` (boolean): Enable responsive table
- `striped` (boolean): Enable striped rows
- `bordered` (boolean): Add table borders
- `hover` (boolean): Enable hover effects

#### Action Buttons Component
**Path:** `components/ui/action-buttons.blade.php`
**Usage:**
```blade
<x-ui.action-buttons :actions="[
    [
        'type' => 'link',
        'url' => route('users.edit', $user),
        'color' => 'primary',
        'icon' => 'bi bi-pencil',
        'text' => 'Edit'
    ],
    [
        'type' => 'form',
        'method' => 'DELETE',
        'url' => route('users.destroy', $user),
        'color' => 'danger',
        'icon' => 'bi bi-trash',
        'confirm' => 'Are you sure?'
    ]
]" />
```
**Props:**
- `actions` (array): Array of action definitions
- `size` (string): Button size (sm, md, lg)
- `alignment` (string): Button group alignment

#### Card Component
**Path:** `components/ui/card.blade.php`
**Usage:**
```blade
<x-ui.card 
    title="Card Title" 
    subtitle="Optional subtitle"
    headerColor="primary"
    :collapsible="true">
    Card content goes here
</x-ui.card>
```
**Props:**
- `title` (string): Card title
- `subtitle` (string): Card subtitle
- `headerColor` (string): Header background color
- `collapsible` (boolean): Make card collapsible
- `collapsed` (boolean): Start collapsed
- `tools` (array): Header tool buttons

### 3. Navigation Components (`components/navigation/`)

#### Sidebar Menu Component
**Path:** `components/navigation/sidebar-menu.blade.php`
**Usage:**
```blade
<x-navigation.sidebar-menu :items="[
    [
        'title' => 'Dashboard',
        'route' => 'dashboard',
        'icon' => 'bi bi-speedometer2'
    ],
    [
        'title' => 'Users',
        'route' => 'users.index',
        'icon' => 'bi bi-people',
        'children' => [
            [
                'title' => 'All Users',
                'route' => 'users.index',
                'icon' => 'bi bi-list'
            ]
        ]
    ]
]" />
```
**Props:**
- `items` (array): Menu items configuration
- `activeRoute` (string): Current active route

### 4. Auth Components (`components/auth/`)

#### Logout Modal Component
**Path:** `components/auth/logout-modal.blade.php`
**Usage:** `<x-auth.logout-modal modalId="customLogoutModal" />`
**Props:**
- `modalId` (string): Modal HTML ID

## Using Components in Views

### Basic Layout Structure
```blade
@extends('layouts.app')

@section('title', 'Page Title')
@section('page-title', 'Page Title')

@section('sidebar')
    <x-navigation.sidebar-menu :items="$menuItems" />
@endsection

@section('content')
    <div class="row">
        <x-ui.small-box color="info" value="123" label="Total Items" />
    </div>
    
    <x-ui.card title="Data Table">
        <x-ui.data-table :headers="['Name', 'Email']">
            {{-- Table content --}}
        </x-ui.data-table>
    </x-ui.card>
@endsection
```

### Component Props Best Practices

1. **Use named props** for better readability:
   ```blade
   <x-ui.alert type="success" :dismissible="true">
   ```

2. **Pass arrays and objects** with colon prefix:
   ```blade
   <x-ui.data-table :headers="$headers" :actions="$actions">
   ```

3. **Use slots** for complex content:
   ```blade
   <x-ui.card title="Complex Content">
       <div class="custom-content">
           <!-- Complex HTML here -->
       </div>
   </x-ui.card>
   ```

## Component Development Guidelines

### 1. Props Validation
Always define default values and validate prop types:
```blade
@props([
    'type' => 'info',
    'dismissible' => true,
    'icon' => null
])
```

### 2. CSS Classes
Use computed CSS classes for dynamic styling:
```blade
@php
    $alertClasses = [
        'success' => 'alert-success',
        'error' => 'alert-danger'
    ];
    $alertClass = $alertClasses[$type] ?? 'alert-info';
@endphp
```

### 3. Conditional Rendering
Use `@if` directives for optional elements:
```blade
@if($dismissible)
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
@endif
```

### 4. Slots
Support both named and default slots:
```blade
<div class="card-header">
    {{ $header ?? $title }}
</div>
<div class="card-body">
    {{ $slot }}
</div>
```

## Integration with JavaScript

Components work with existing JavaScript frameworks:

### DataTable Integration
```blade
<x-ui.data-table id="usersTable">
    {{-- content --}}
</x-ui.data-table>

@section('scripts')
<script>
    new DataTableManager('#usersTable');
</script>
@endsection
```

### Form Validation
```blade
<x-ui.card>
    <form id="userForm">
        {{-- form content --}}
    </form>
</x-ui.card>

@section('scripts')  
<script>
    new FormValidator('#userForm');
</script>
@endsection
```

## Migration Guide

### From Old Views to Components

**Before:**
```blade
<div class="alert alert-success alert-dismissible">
    <button type="button" class="close" data-dismiss="alert">&times;</button>
    {{ session('success') }}
</div>
```

**After:**
```blade
<x-ui.session-messages />
```

**Before:**
```blade
<div class="small-box bg-info">
    <div class="inner">
        <h3>{{ $totalUsers }}</h3>
        <p>Total Users</p>
    </div>
    <div class="icon">
        <i class="bi bi-people"></i>
    </div>
</div>
```

**After:**
```blade
<x-ui.small-box 
    color="info" 
    :value="$totalUsers" 
    label="Total Users" 
    icon="bi bi-people" />
```

## Performance Considerations

1. **Component Caching**: Laravel automatically caches compiled Blade components
2. **Prop Validation**: Minimal overhead for prop type checking  
3. **CSS Optimization**: Components use shared CSS classes to minimize duplication
4. **JavaScript Integration**: Components work with existing JS without conflicts

## Future Enhancements

1. **Form Components**: Input fields, selects, checkboxes
2. **Chart Components**: Integration with Chart.js
3. **Modal Components**: Reusable modal dialogs
4. **Notification Components**: Toast notifications
5. **Theme Components**: Dynamic theming support

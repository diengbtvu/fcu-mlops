@extends('layouts.app')

@section('title', 'AI API Keys')

@section('sidebar')
<x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="container-fluid">
    <div class="row">
        <div class="col-12 col-xl-9">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title"><i class="bi bi-key"></i> AI API Keys</h3>
                    <p class="text-muted mb-0">Groq key pool for report explanations and benchmark evaluation.</p>
                </div>
                <div class="card-body">
                    @if(session('success'))
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            <i class="bi bi-check-circle"></i> {{ session('success') }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    @endif

                    @if(session('error'))
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <i class="bi bi-exclamation-triangle"></i> {{ session('error') }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    @endif

                    <div class="mb-4">
                        <div class="d-flex align-items-center gap-3 flex-wrap mb-2">
                            <span class="badge bg-primary">{{ $groqKeyCount }} Groq key{{ $groqKeyCount === 1 ? '' : 's' }}</span>
                        </div>
                        @if(empty($maskedGroqKeys))
                            <div class="text-muted small">No Groq keys are saved in the database yet.</div>
                        @else
                            <div class="list-group">
                                @foreach($maskedGroqKeys as $maskedKey)
                                    <div class="list-group-item d-flex align-items-center justify-content-between gap-3">
                                        <code class="bg-light border rounded px-2 py-1">{{ $maskedKey['label'] }}</code>
                                        <form action="{{ route('admin.settings.update-ai') }}" method="POST" class="m-0">
                                            @csrf
                                            @method('PUT')
                                            <input type="hidden" name="delete_groq_key_index" value="{{ $maskedKey['index'] }}">
                                            <button type="submit" class="btn btn-sm btn-outline-danger">
                                                <i class="bi bi-trash"></i> Delete
                                            </button>
                                        </form>
                                    </div>
                                @endforeach
                            </div>
                        @endif
                    </div>

                    <form action="{{ route('admin.settings.update-ai') }}" method="POST">
                        @csrf
                        @method('PUT')

                        <div class="mb-3">
                            <label for="groq_api_keys" class="form-label fw-bold">
                                Add Groq API keys
                            </label>
                            <textarea
                                class="form-control @error('groq_api_keys') is-invalid @enderror"
                                id="groq_api_keys"
                                name="groq_api_keys"
                                rows="8"
                                spellcheck="false"
                                autocomplete="off"
                                placeholder="Paste new Groq API keys, one per line. Existing saved keys will be kept.">{{ old('groq_api_keys') }}</textarea>
                            @error('groq_api_keys')
                                <div class="invalid-feedback">{{ $message }}</div>
                            @enderror
                            <div class="form-text">
                                Stored encrypted. New keys are merged into the existing pool and duplicates are skipped.
                            </div>
                        </div>

                        <div class="d-flex gap-2">
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-plus-circle"></i> Add keys
                            </button>
                            <a href="{{ route('admin.datasets.index') }}" class="btn btn-outline-secondary">
                                <i class="bi bi-arrow-left"></i> Back to datasets
                            </a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

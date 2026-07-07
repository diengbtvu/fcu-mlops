@extends('layouts.app')

@section('title', __('models.machine_learning_models') . ' - Benchmark Evaluation')
@section('page-title', 'Benchmark Evaluation')

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route(($routeNamespace ?? 'admin') . '.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route(($routeNamespace ?? 'admin') . '.models') }}">{{ __('nav.models') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route(($routeNamespace ?? 'admin') . '.models.report', $model) }}">Training Report</a></li>
    <li class="breadcrumb-item active">Benchmark Evaluation</li>
@endsection

@section('sidebar')
@if(auth()->user()->role_id == 1)
    <x-navigation.admin-sidebar />
@else
    <x-navigation.user-sidebar />
@endif
@endsection

@section('styles')
<style>
    .benchmark-hero {
        background:
            radial-gradient(circle at top right, rgba(125, 211, 252, 0.28), transparent 36%),
            radial-gradient(circle at bottom left, rgba(56, 189, 248, 0.18), transparent 42%),
            linear-gradient(135deg, #0b132b 0%, #12324a 52%, #155e75 100%);
        border: 0;
        border-radius: 22px;
        color: #f8fbff;
        overflow: hidden;
        box-shadow: 0 18px 48px rgba(15, 23, 42, 0.16);
        position: relative;
    }

    .benchmark-hero::after {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(5, 11, 27, 0.34) 0%, rgba(5, 11, 27, 0.16) 45%, rgba(255, 255, 255, 0) 100%);
        pointer-events: none;
    }

    .benchmark-hero .metric-tile {
        background: rgba(8, 19, 37, 0.46);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 16px;
        min-height: 108px;
        padding: 1rem;
        backdrop-filter: blur(12px);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    .benchmark-hero .hero-metrics {
        position: relative;
        z-index: 1;
    }

    .benchmark-hero h2,
    .benchmark-hero p,
    .benchmark-hero .metric-tile,
    .benchmark-hero .benchmark-chip {
        position: relative;
        z-index: 1;
    }

    .benchmark-hero h2 {
        color: #ffffff;
        text-shadow: 0 4px 22px rgba(15, 23, 42, 0.45);
    }

    .benchmark-hero p {
        color: rgba(248, 250, 252, 0.92);
    }

    .benchmark-hero .metric-tile .display-6,
    .benchmark-hero .metric-tile .small,
    .benchmark-hero .metric-tile .text-uppercase {
        color: #f8fbff;
    }

    .benchmark-panel {
        border: 1px solid rgba(15, 23, 42, 0.08);
        border-radius: 18px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.05);
    }

    .benchmark-panel .card-header {
        border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    }

    .benchmark-stat {
        border: 1px solid rgba(15, 23, 42, 0.08);
        border-radius: 16px;
        padding: 1rem;
        background: #fff;
        height: 100%;
    }

    .benchmark-stat-subtle {
        background: linear-gradient(180deg, #f8fbff 0%, #eef5fb 100%);
    }

    .benchmark-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.4rem 0.8rem;
        border-radius: 999px;
        background: #eef5fb;
        color: #12324a;
        font-size: 0.875rem;
        font-weight: 700;
    }

    .benchmark-chip b {
        font-weight: 800;
    }

    .benchmark-table thead th {
        white-space: nowrap;
        font-size: 0.77rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #52606d;
        background: #f8fafc;
    }

    .benchmark-table td {
        vertical-align: middle;
    }

    .benchmark-table .row-highlight {
        background: #ecfdf5;
    }

    .benchmark-wide-table {
        width: 100%;
        table-layout: fixed;
    }

    .benchmark-wide-table thead th {
        white-space: normal;
        line-height: 1.25;
    }

    .benchmark-wide-table td,
    .benchmark-wide-table th {
        word-break: break-word;
        overflow-wrap: anywhere;
    }

    .benchmark-wide-table .artifact-col {
        width: 22%;
    }

    .benchmark-wide-table .relation-col {
        width: 12%;
    }

    .benchmark-wide-table .value-col {
        width: 10%;
    }

    .benchmark-wide-table .gold-col {
        width: 9%;
    }

    .benchmark-wide-table .delta-col {
        width: 7%;
        white-space: nowrap;
    }

    .benchmark-wide-table th:nth-child(2),
    .benchmark-wide-table td:nth-child(2) {
        width: 5%;
    }

    .benchmark-wide-table th:nth-child(3),
    .benchmark-wide-table td:nth-child(3) {
        width: 6%;
    }

    .benchmark-wide-table th:nth-child(4),
    .benchmark-wide-table td:nth-child(4) {
        width: 9%;
    }

    .benchmark-wide-table th:nth-child(5),
    .benchmark-wide-table td:nth-child(5) {
        width: 10%;
    }

    .benchmark-wide-table .subject-col {
        width: 10%;
    }

    .benchmark-wide-table td:nth-child(2),
    .benchmark-wide-table td:nth-child(3),
    .benchmark-wide-table td:nth-child(10) {
        text-align: center;
    }

    .benchmark-sticky-header thead th {
        position: sticky;
        top: 0;
        z-index: 3;
        background: #f8fafc;
        box-shadow: inset 0 -1px 0 rgba(15, 23, 42, 0.08);
    }

    .benchmark-sticky-wrap {
        overflow-x: auto;
        overflow-y: visible;
    }

    .benchmark-floating-header-shell {
        position: fixed;
        display: none;
        overflow: hidden;
        background: #f8fafc;
        border: 1px solid rgba(15, 23, 42, 0.08);
        border-radius: 12px 12px 0 0;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
        pointer-events: none;
    }

    .benchmark-floating-header-table {
        margin-bottom: 0;
        background: #f8fafc;
        table-layout: fixed;
    }

    .benchmark-floating-header-table thead th {
        background: #f8fafc;
        vertical-align: middle;
    }

    .benchmark-status-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        max-width: 100%;
        padding: 0.22rem 0.45rem;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        text-align: center;
        white-space: nowrap;
        line-height: 1.1;
    }

    .benchmark-status-success {
        background: #dcfce7;
        color: #166534;
    }

    .benchmark-status-warning {
        background: #fef3c7;
        color: #92400e;
    }

    .benchmark-status-danger {
        background: #fee2e2;
        color: #991b1b;
    }

    .benchmark-status-secondary {
        background: #e2e8f0;
        color: #334155;
    }

    .benchmark-status-dark {
        background: #e5e7eb;
        color: #111827;
    }

    @media (max-width: 991.98px) {
        .benchmark-hero .metric-tile {
            min-height: auto;
        }

        .benchmark-wide-table {
            table-layout: auto;
        }

        .benchmark-wide-table td,
        .benchmark-wide-table th {
            white-space: normal;
        }
    }
</style>
@endsection

@section('content')
@php
    $routeNamespace = $routeNamespace ?? 'admin';
    $benchmarkSummary = is_array($summary['benchmark_summary'] ?? null) ? $summary['benchmark_summary'] : [];
    $benchmarkStatusPayload = is_array($benchmarkStatusPayload ?? null) ? $benchmarkStatusPayload : [];
    $leaderboardPayload = is_array($benchmarkLeaderboardPayload ?? null) ? $benchmarkLeaderboardPayload : [];
    $runMetadataPayload = is_array($benchmarkRunMetadataPayload ?? null) ? $benchmarkRunMetadataPayload : [];
    $selectedPayload = is_array($benchmarkSelectedPayload ?? null) ? $benchmarkSelectedPayload : [];
    $benchmarkClaimComparisonRows = is_array($benchmarkClaimComparisonRows ?? null)
        ? $benchmarkClaimComparisonRows
        : [];
    $leaderboardRows = is_array($leaderboardPayload['leaderboard'] ?? null) ? $leaderboardPayload['leaderboard'] : [];
    $artifactScoreRows = is_array($leaderboardPayload['artifact_scores'] ?? null) ? $leaderboardPayload['artifact_scores'] : [];
    $reportAssets = is_array($reportAssets ?? null) ? $reportAssets : [];
    $selectedAssetPayloads = is_array($selectedPayload['assets'] ?? null) ? $selectedPayload['assets'] : [];
    $visibleBenchmarkArms = ['A', 'B', 'C', 'D'];
    $leaderboardRows = array_values(array_filter(
        $leaderboardRows,
        fn ($row) => in_array((string) ($row['arm'] ?? ''), $visibleBenchmarkArms, true)
    ));
    $artifactScoreRows = array_values(array_filter(
        $artifactScoreRows,
        fn ($row) => in_array((string) ($row['arm'] ?? ''), $visibleBenchmarkArms, true)
    ));
    $benchmarkClaimComparisonRows = array_values(array_filter(
        $benchmarkClaimComparisonRows,
        fn ($row) => in_array((string) ($row['arm'] ?? ''), $visibleBenchmarkArms, true)
    ));

    $benchmarkStatus = strtolower(trim((string) ($benchmarkStatusPayload['status'] ?? '')));
    $bestOverall = is_array($benchmarkSummary['best_overall'] ?? null)
        ? $benchmarkSummary['best_overall']
        : (is_array($leaderboardRows[0] ?? null) ? $leaderboardRows[0] : []);
    if (!in_array((string) ($bestOverall['arm'] ?? ''), $visibleBenchmarkArms, true)) {
        $bestOverall = is_array($leaderboardRows[0] ?? null) ? $leaderboardRows[0] : [];
    }
    $selectedRow = is_array($selectedPayload['selected_row'] ?? null)
        ? $selectedPayload['selected_row']
        : (is_array($benchmarkSummary['selected_explanations'] ?? null) ? $benchmarkSummary['selected_explanations'] : []);

    $benchmarkWarnings = [];
    if (is_array($benchmarkSummary['warnings'] ?? null)) {
        $benchmarkWarnings = array_merge($benchmarkWarnings, $benchmarkSummary['warnings']);
    }
    if (is_array($runMetadataPayload['warnings'] ?? null)) {
        $benchmarkWarnings = array_merge($benchmarkWarnings, $runMetadataPayload['warnings']);
    }
    $benchmarkWarnings = array_values(array_unique(array_filter(array_map('strval', $benchmarkWarnings))));

    $formatMetric = function ($value, int $precision = 3): string {
        if (!is_numeric($value)) {
            return 'n/a';
        }
        return number_format((float) $value, $precision);
    };

    $formatTimestamp = function ($value): string {
        $value = trim((string) $value);
        if ($value === '') {
            return 'n/a';
        }

        try {
            return \Carbon\Carbon::parse($value)->format('Y-m-d H:i:s');
        } catch (\Throwable $e) {
            return $value;
        }
    };

    $metricTone = function ($value, bool $inverse = false): string {
        $numeric = is_numeric($value) ? (float) $value : null;
        if ($numeric === null) {
            return 'secondary';
        }

        if ($inverse) {
            if ($numeric <= 0.10) {
                return 'success';
            }
            if ($numeric <= 0.30) {
                return 'warning';
            }
            return 'danger';
        }

        if ($numeric >= 0.50) {
            return 'success';
        }
        if ($numeric >= 0.25) {
            return 'warning';
        }
        return 'danger';
    };

    $normalizeMixedList = function ($items, bool $includeCounts = false): array {
        if (!is_array($items)) {
            return [];
        }

        $normalized = [];
        foreach ($items as $item) {
            if (is_scalar($item) || $item === null) {
                $text = trim((string) $item);
            } elseif (is_array($item)) {
                $reason = trim((string) ($item['reason'] ?? $item['label'] ?? $item['name'] ?? ''));
                $count = isset($item['count']) && is_numeric($item['count']) ? (int) $item['count'] : null;
                $text = $reason;
                if ($includeCounts && $reason !== '' && $count !== null) {
                    $text .= " ({$count})";
                } elseif ($text === '') {
                    $text = trim((string) json_encode($item));
                }
            } else {
                $text = trim((string) json_encode($item));
            }

            if ($text !== '') {
                $normalized[] = $text;
            }
        }

        return array_values(array_unique($normalized));
    };

    $downloadLinks = [
        ['label' => 'Leaderboard JSON', 'asset' => $reportAssets['benchmark_leaderboard_json'] ?? null],
        ['label' => 'Leaderboard CSV', 'asset' => $reportAssets['benchmark_leaderboard_csv'] ?? null],
        ['label' => 'Per-chart JSON', 'asset' => $reportAssets['benchmark_per_chart_json'] ?? null],
        ['label' => 'Per-chart CSV', 'asset' => $reportAssets['benchmark_per_chart_csv'] ?? null],
        ['label' => 'Run Metadata', 'asset' => $reportAssets['benchmark_run_metadata'] ?? null],
        ['label' => 'Manifest', 'asset' => $reportAssets['benchmark_manifest'] ?? null],
        ['label' => 'Selected Explanations', 'asset' => $reportAssets['benchmark_selected_explanations'] ?? null],
    ];
    $runArms = array_values(array_filter(
        $normalizeMixedList($runMetadataPayload['arms'] ?? null),
        fn ($arm) => in_array($arm, $visibleBenchmarkArms, true)
    ));
    $runConditions = $normalizeMixedList($runMetadataPayload['conditions'] ?? null);
    $displayGenerationCount = !empty($artifactScoreRows)
        ? count($artifactScoreRows)
        : (int) ($runMetadataPayload['generation_count'] ?? $benchmarkSummary['generation_count'] ?? 0);
    $claimStatusCounts = [];
    foreach ($benchmarkClaimComparisonRows as $row) {
        $status = trim((string) ($row['status'] ?? ''));
        if ($status === '') {
            continue;
        }
        $claimStatusCounts[$status] = ($claimStatusCounts[$status] ?? 0) + 1;
    }
@endphp

<div class="row mb-3">
    <div class="col-12 d-flex flex-wrap gap-2">
        <a href="{{ route($routeNamespace . '.models.report', $model) }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> Back to Report
        </a>
        <a href="{{ route($routeNamespace . '.models') }}" class="btn btn-outline-secondary">
            <i class="bi bi-grid"></i> All Models
        </a>
        @foreach($downloadLinks as $download)
            @if(is_array($download['asset'] ?? null) && !empty($download['asset']['url']))
                <a href="{{ $download['asset']['url'] }}" class="btn btn-outline-primary" target="_blank" rel="noopener">
                    <i class="bi bi-download"></i> {{ $download['label'] }}
                </a>
            @endif
        @endforeach
    </div>
</div>

<div class="card benchmark-hero mb-4">
    <div class="card-body p-4 p-xl-5">
        <div class="row g-3 hero-metrics">
            <div class="col-lg-3 col-sm-6">
                <div class="metric-tile">
                    <div class="text-uppercase small mb-2" style="letter-spacing: 0.08em; opacity: 0.8;">Best Fact F1</div>
                    <div class="display-6 fw-bold">{{ $formatMetric($bestOverall['fact_f1'] ?? null) }}</div>
                    <div class="small mt-2 opacity-75">
                        {{ $bestOverall['arm'] ?? 'n/a' }} · {{ $bestOverall['input_condition'] ?? 'n/a' }}
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-sm-6">
                <div class="metric-tile">
                    <div class="text-uppercase small mb-2" style="letter-spacing: 0.08em; opacity: 0.8;">Artifact Coverage</div>
                    <div class="display-6 fw-bold">{{ (int) ($runMetadataPayload['artifact_count'] ?? $benchmarkSummary['artifact_count'] ?? 0) }}</div>
                    <div class="small mt-2 opacity-75">
                        {{ count($artifactScoreRows) }} artifact score row(s) loaded
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-sm-6">
                <div class="metric-tile">
                    <div class="text-uppercase small mb-2" style="letter-spacing: 0.08em; opacity: 0.8;">Generations</div>
                    <div class="display-6 fw-bold">{{ $displayGenerationCount }}</div>
                    <div class="small mt-2 opacity-75">
                        {{ count($leaderboardRows) }} leaderboard row(s)
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-sm-6">
                <div class="metric-tile">
                    <div class="text-uppercase small mb-2" style="letter-spacing: 0.08em; opacity: 0.8;">Website Selection</div>
                    <div class="display-6 fw-bold">{{ $selectedPayload['selected_arm'] ?? ($selectedRow['arm'] ?? 'n/a') }}</div>
                    <div class="small mt-2 opacity-75">
                        {{ $selectedPayload['selected_condition'] ?? ($selectedRow['input_condition'] ?? 'n/a') }}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

@if($summaryError)
    <div class="alert alert-warning">
        <i class="bi bi-exclamation-triangle"></i> {{ $summaryError }}
    </div>
@endif

@if($benchmarkStatus === 'pending')
    <div class="alert alert-info">
        <div class="fw-bold mb-1">Benchmark generation is still running</div>
        <div class="small">
            Status: {{ $benchmarkStatusPayload['message'] ?? 'pending' }}
            @if(!empty($benchmarkStatusPayload['progress']))
                · Progress {{ number_format((float) $benchmarkStatusPayload['progress'], 0) }}%
            @endif
        </div>
    </div>
@elseif(empty($leaderboardRows) && empty($artifactScoreRows))
    <div class="alert alert-secondary">
        <div class="fw-bold mb-1">No benchmark payload was loaded</div>
        <div class="small">The page is ready, but this report does not currently expose a full benchmark result set.</div>
    </div>
@endif

@if(!empty($benchmarkWarnings))
    <div class="alert alert-light border">
        <div class="fw-bold mb-2">Warnings</div>
        @foreach($benchmarkWarnings as $warning)
            <div class="small">{{ $warning }}</div>
        @endforeach
    </div>
@endif

<div class="row g-3 mb-4">
    <div class="col-lg-3 col-md-6">
        <div class="benchmark-stat benchmark-stat-subtle">
            <div class="text-muted small mb-1">Best Leaderboard Row</div>
            <div class="h5 mb-2">{{ $bestOverall['arm'] ?? 'n/a' }} · {{ $bestOverall['input_condition'] ?? 'n/a' }}</div>
            <div class="small">
                Fact F1={{ $formatMetric($bestOverall['fact_f1'] ?? null) }}<br>
                Precision={{ $formatMetric($bestOverall['fact_precision'] ?? null) }}<br>
                Recall={{ $formatMetric($bestOverall['fact_recall'] ?? null) }}
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-md-6">
        <div class="benchmark-stat">
            <div class="text-muted small mb-1">Selected Row Metrics</div>
            <div class="h5 mb-2">{{ $selectedRow['arm'] ?? 'n/a' }} · {{ $selectedRow['input_condition'] ?? 'n/a' }}</div>
            <div class="small">
                Fact F1={{ $formatMetric($selectedRow['fact_f1'] ?? null) }}<br>
                Precision={{ $formatMetric($selectedRow['fact_precision'] ?? null) }}<br>
                Recall={{ $formatMetric($selectedRow['fact_recall'] ?? null) }}
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-md-6">
        <div class="benchmark-stat">
            <div class="text-muted small mb-1">Website Uses</div>
            <div class="h5 mb-2">{{ $selectedPayload['selected_arm'] ?? ($selectedRow['arm'] ?? 'n/a') }} · {{ $selectedPayload['selected_condition'] ?? ($selectedRow['input_condition'] ?? 'n/a') }}</div>
            <div class="small">
                Selection method: {{ $selectedPayload['selection_method'] ?? 'n/a' }}<br>
                Explanation assets: {{ count($selectedAssetPayloads) }}
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-md-6">
        <div class="benchmark-stat">
            <div class="text-muted small mb-1">Run Metadata</div>
            <div class="h5 mb-2">{{ $runMetadataPayload['client'] ?? 'n/a' }} · {{ $runMetadataPayload['client_model'] ?? 'n/a' }}</div>
            <div class="small">
                Arms: {{ implode(', ', $runArms) ?: 'n/a' }}<br>
                Conditions: {{ implode(', ', $runConditions) ?: 'n/a' }}<br>
                Generated: {{ $formatTimestamp($runMetadataPayload['created_at'] ?? $benchmarkSummary['generated_at'] ?? null) }}
            </div>
        </div>
    </div>
</div>

<div class="card benchmark-panel mb-4">
    <div class="card-header bg-white d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div>
            <div class="fw-bold">Leaderboard</div>
            <div class="small text-muted">Each row is one arm + input condition pair aggregated across the benchmark run.</div>
        </div>
        <div class="small text-muted">
            {{ count($leaderboardRows) }} row(s) · {{ count($artifactScoreRows) }} artifact score row(s)
        </div>
    </div>
    <div class="card-body p-0">
        @if(empty($leaderboardRows))
            <div class="p-4 text-muted">No leaderboard rows were loaded.</div>
        @else
            <div class="table-responsive">
                <table class="table table-sm benchmark-table align-middle mb-0">
                    <thead>
                        <tr>
                            <th>Arm</th>
                            <th>Condition</th>
                            <th>Fact F1</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>Unsupported</th>
                            <th>Contradiction</th>
                            <th>Coverage</th>
                            <th>Numeric</th>
                            <th>Artifacts</th>
                            <th>Claims</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($leaderboardRows as $row)
                            @php
                                $isSelectedRow = ($row['arm'] ?? null) === ($selectedPayload['selected_arm'] ?? $selectedRow['arm'] ?? null)
                                    && ($row['input_condition'] ?? null) === ($selectedPayload['selected_condition'] ?? $selectedRow['input_condition'] ?? null);
                            @endphp
                            <tr class="{{ $isSelectedRow ? 'row-highlight' : '' }}">
                                <td class="fw-bold">{{ $row['arm'] ?? 'n/a' }}</td>
                                <td>{{ $row['input_condition'] ?? 'n/a' }}</td>
                                <td><span class="badge bg-{{ $metricTone($row['fact_f1'] ?? null) }}">{{ $formatMetric($row['fact_f1'] ?? null) }}</span></td>
                                <td>{{ $formatMetric($row['fact_precision'] ?? null) }}</td>
                                <td>{{ $formatMetric($row['fact_recall'] ?? null) }}</td>
                                <td><span class="badge bg-{{ $metricTone($row['unsupported_claim_rate'] ?? null, true) }}">{{ $formatMetric($row['unsupported_claim_rate'] ?? null) }}</span></td>
                                <td>{{ $formatMetric($row['contradiction_rate'] ?? null) }}</td>
                                <td>{{ $formatMetric($row['coverage_of_salient_facts'] ?? null) }}</td>
                                <td>{{ $formatMetric($row['numeric_accuracy'] ?? null) }}</td>
                                <td>{{ (int) ($row['artifact_count'] ?? 0) }}</td>
                                <td>{{ (int) ($row['claim_count'] ?? 0) }}</td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        @endif
    </div>
</div>

<div class="card benchmark-panel mb-4">
    <div class="card-header bg-white d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div>
            <div class="fw-bold">Claim vs Gold Detail</div>
            <div class="small text-muted">Compact structured comparison between extracted claim values and matched gold values.</div>
        </div>
        <div class="d-flex align-items-center flex-wrap gap-2">
            <div class="small text-muted">{{ count($benchmarkClaimComparisonRows) }} detail row(s)</div>
            @foreach($claimStatusCounts as $status => $count)
                @php
                    $statusTone = match ($status) {
                        'supported' => 'success',
                        'partially_supported' => 'warning',
                        'contradicted' => 'danger',
                        'unverifiable' => 'secondary',
                        'no_claims' => 'dark',
                        default => 'secondary',
                    };
                    $statusLabel = ucwords(str_replace('_', ' ', $status));
                @endphp
                <span class="benchmark-status-pill benchmark-status-{{ $statusTone }}">{{ $statusLabel }} · {{ $count }}</span>
            @endforeach
        </div>
    </div>
    <div class="card-body p-0">
        @if(empty($benchmarkClaimComparisonRows))
            <div class="p-4 text-muted">No claim-level verification rows were loaded for this benchmark run.</div>
        @else
            <div class="table-responsive benchmark-sticky-wrap" data-benchmark-sticky-wrap>
                <table class="table table-sm benchmark-table benchmark-wide-table benchmark-sticky-header align-middle mb-0" data-benchmark-sticky-table>
                    <thead>
                        <tr>
                            <th class="artifact-col">Artifact</th>
                            <th>Arm</th>
                            <th>Level</th>
                            <th>Status</th>
                            <th>Claim Type</th>
                            <th class="subject-col">Subject</th>
                            <th class="relation-col">Metric / Predicate</th>
                            <th class="value-col">Value / Object</th>
                            <th class="gold-col">Gold Value</th>
                            <th class="delta-col">Delta</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($benchmarkClaimComparisonRows as $row)
                            <tr>
                                <td class="artifact-col">
                                    <div class="fw-bold">{{ $row['artifact_title'] ?? 'n/a' }}</div>
                                    <div class="small text-muted mt-1">{{ $row['artifact_scope'] ?? 'n/a' }}</div>
                                </td>
                                <td class="fw-bold">{{ $row['arm'] ?? 'n/a' }}</td>
                                <td>{{ $row['semantic_level'] ?? '-' }}</td>
                                <td>
                                    <span class="benchmark-status-pill benchmark-status-{{ $row['status_tone'] ?? 'secondary' }}">
                                        {{ ucwords(str_replace('_', ' ', (string) ($row['status'] ?? 'n/a'))) }}
                                    </span>
                                </td>
                                <td>{{ $row['claim_type'] ?? 'n/a' }}</td>
                                <td class="subject-col">{{ $row['claim_subject'] ?? 'n/a' }}</td>
                                <td class="relation-col">{{ $row['claim_relation'] ?? 'n/a' }}</td>
                                <td class="value-col">{{ $row['claim_value'] ?? 'n/a' }}</td>
                                <td class="gold-col">{{ $row['gold_value'] ?? 'n/a' }}</td>
                                <td class="delta-col">
                                    @if(isset($row['numeric_delta']) && is_numeric($row['numeric_delta']))
                                        {{ number_format((float) $row['numeric_delta'], 6) }}
                                    @else
                                        -
                                    @endif
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        @endif
    </div>
</div>
@endsection

@section('scripts')
<script>
document.addEventListener('DOMContentLoaded', () => {
    const stickyWraps = Array.from(document.querySelectorAll('[data-benchmark-sticky-wrap]'));
    if (!stickyWraps.length) {
        return;
    }

    const getTopOffset = () => {
        const navbar = document.querySelector('.main-header.navbar');
        if (!navbar) {
            return 0;
        }
        return Math.max(Math.ceil(navbar.getBoundingClientRect().bottom), 0);
    };

    stickyWraps.forEach((wrap) => {
        const table = wrap.querySelector('[data-benchmark-sticky-table]');
        const sourceHead = table?.querySelector('thead');
        if (!table || !sourceHead) {
            return;
        }

        const floatingShell = document.createElement('div');
        floatingShell.className = 'benchmark-floating-header-shell';
        floatingShell.setAttribute('aria-hidden', 'true');

        const floatingTable = document.createElement('table');
        floatingTable.className = table.className.replace(/\bbenchmark-sticky-header\b/g, '').trim() + ' benchmark-floating-header-table';

        const clonedHead = sourceHead.cloneNode(true);
        floatingTable.appendChild(clonedHead);
        floatingShell.appendChild(floatingTable);
        document.body.appendChild(floatingShell);

        const sourceCells = () => Array.from(sourceHead.querySelectorAll('th'));
        const clonedCells = () => Array.from(clonedHead.querySelectorAll('th'));

        const syncColumnWidths = () => {
            const originalCells = sourceCells();
            const replicaCells = clonedCells();
            replicaCells.forEach((cell, index) => {
                const width = originalCells[index]?.getBoundingClientRect().width ?? 0;
                if (width > 0) {
                    const pxWidth = `${Math.ceil(width)}px`;
                    cell.style.width = pxWidth;
                    cell.style.minWidth = pxWidth;
                    cell.style.maxWidth = pxWidth;
                }
            });
            floatingTable.style.width = `${Math.ceil(table.getBoundingClientRect().width)}px`;
        };

        const syncHorizontalScroll = () => {
            floatingTable.style.transform = `translateX(${-wrap.scrollLeft}px)`;
        };

        const updateFloatingHeader = () => {
            const topOffset = getTopOffset();
            const wrapRect = wrap.getBoundingClientRect();
            const tableRect = table.getBoundingClientRect();
            const headRect = sourceHead.getBoundingClientRect();
            const headHeight = Math.ceil(headRect.height);
            const shouldShow =
                tableRect.top < topOffset &&
                tableRect.bottom > topOffset + headHeight &&
                wrapRect.width > 0;

            if (!shouldShow) {
                floatingShell.style.display = 'none';
                return;
            }

            syncColumnWidths();
            syncHorizontalScroll();

            floatingShell.style.display = 'block';
            floatingShell.style.top = `${topOffset}px`;
            floatingShell.style.left = `${Math.round(wrapRect.left)}px`;
            floatingShell.style.width = `${Math.round(wrapRect.width)}px`;
            floatingShell.style.height = `${headHeight}px`;
            floatingShell.style.zIndex = '1025';
        };

        let frame = null;
        const queueUpdate = () => {
            if (frame !== null) {
                return;
            }
            frame = window.requestAnimationFrame(() => {
                frame = null;
                updateFloatingHeader();
            });
        };

        wrap.addEventListener('scroll', queueUpdate, { passive: true });
        window.addEventListener('scroll', queueUpdate, { passive: true });
        window.addEventListener('resize', queueUpdate);

        if ('ResizeObserver' in window) {
            const resizeObserver = new ResizeObserver(queueUpdate);
            resizeObserver.observe(wrap);
            resizeObserver.observe(table);
        }

        queueUpdate();
    });
});
</script>
@endsection

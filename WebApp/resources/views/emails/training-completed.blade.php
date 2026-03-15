<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Training Notification</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .email-container {
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            padding-bottom: 20px;
            border-bottom: 3px solid #4CAF50;
            margin-bottom: 20px;
        }
        .header.failed {
            border-bottom-color: #dc3545;
        }
        .header h1 {
            margin: 0;
            color: #4CAF50;
            font-size: 24px;
        }
        .header.failed h1 {
            color: #dc3545;
        }
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
            font-size: 14px;
        }
        .status-badge.success {
            background-color: #d4edda;
            color: #155724;
        }
        .status-badge.failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        .info-section {
            margin: 20px 0;
        }
        .info-row {
            display: flex;
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        .info-row:last-child {
            border-bottom: none;
        }
        .info-label {
            font-weight: bold;
            width: 180px;
            color: #555;
        }
        .info-value {
            flex: 1;
            color: #333;
        }
        .metrics-section {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .metrics-section h3 {
            margin-top: 0;
            color: #333;
            font-size: 18px;
        }
        .metric-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px dashed #ddd;
        }
        .metric-item:last-child {
            border-bottom: none;
        }
        .metric-label {
            font-weight: 600;
            color: #555;
        }
        .metric-value {
            color: #007bff;
            font-weight: bold;
        }
        .error-section {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .error-section h3 {
            margin-top: 0;
            color: #856404;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #777;
            font-size: 14px;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }
        .button:hover {
            background-color: #0056b3;
        }
        .icon {
            font-size: 48px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header {{ $result['success'] ? '' : 'failed' }}">
            <div class="icon">{{ $result['success'] ? '✅' : '❌' }}</div>
            <h1>Model Training {{ $result['success'] ? 'Completed' : 'Failed' }}</h1>
            <span class="status-badge {{ $result['success'] ? 'success' : 'failed' }}">
                {{ $result['success'] ? 'SUCCESS' : 'FAILED' }}
            </span>
        </div>

        <div class="info-section">
            <h3>Training Information</h3>
            <div class="info-row">
                <span class="info-label">Model Type:</span>
                <span class="info-value"><strong>{{ strtoupper($trainingData['model_type']) }}</strong></span>
            </div>
            @if(isset($trainingData['dataset_path']))
            <div class="info-row">
                <span class="info-label">Dataset:</span>
                <span class="info-value">{{ basename($trainingData['dataset_path']) }}</span>
            </div>
            @endif
            @if(isset($trainingData['dataset_name']))
            <div class="info-row">
                <span class="info-label">Dataset:</span>
                <span class="info-value">{{ $trainingData['dataset_name'] }}</span>
            </div>
            @endif
            <div class="info-row">
                <span class="info-label">Model Name:</span>
                <span class="info-value">{{ $trainingData['model_name'] }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Training Date:</span>
                <span class="info-value">{{ date('Y-m-d H:i:s') }}</span>
            </div>
            @if(isset($trainingData['test_size']))
            <!-- <div class="info-row">
                <span class="info-label">Test Size:</span>
                <span class="info-value">{{ $trainingData['test_size'] * 100 }}%</span>
            </div> -->
            @endif
        </div>

        @if($result['success'] && isset($result['data']['metrics']))
        <div class="metrics-section">
            <h3>📊 Model Performance Metrics</h3>
            @foreach($result['data']['metrics'] as $key => $value)
            <div class="metric-item">
                <span class="metric-label">{{ ucwords(str_replace('_', ' ', $key)) }}:</span>
                <span class="metric-value">
                    @if(is_numeric($value))
                        {{ number_format($value, 4) }}
                    @else
                        {{ $value }}
                    @endif
                </span>
            </div>
            @endforeach
        </div>
        @endif

        @if($result['success'] && isset($result['data']['mlflow_info']))
        <div class="info-section">
            <h3>🔬 MLflow Tracking</h3>
            <div class="info-row">
                <span class="info-label">Run ID:</span>
                <span class="info-value" style="font-family: monospace; font-size: 12px;">{{ $result['data']['mlflow_info']['run_id'] }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Experiment ID:</span>
                <span class="info-value">{{ $result['data']['mlflow_info']['experiment_id'] }}</span>
            </div>
            @if(isset($result['data']['mlflow_info']['model_uri']))
            <div class="info-row">
                <span class="info-label">Model URI:</span>
                <span class="info-value" style="font-size: 12px;">{{ $result['data']['mlflow_info']['model_uri'] }}</span>
            </div>
            @endif
        </div>
        @endif

        @if(!$result['success'])
        <div class="error-section">
            <h3>⚠️ Error Details</h3>
            <p><strong>Message:</strong> {{ $result['message'] ?? 'Unknown error occurred' }}</p>
            @if(isset($result['error']))
            <p><strong>Technical Details:</strong></p>
            <pre style="background: white; padding: 10px; border-radius: 4px; overflow-x: auto;">{{ $result['error'] }}</pre>
            @endif
        </div>
        @endif

        <div style="text-align: center;">
            <a href="{{ url('/admin/datasets') }}" class="button">
                View Models Dashboard
            </a>
        </div>

        <div class="footer">
            <p>This is an automated notification from your ML Training System.</p>
            <p>© {{ date('Y') }} Hydrogen Production Rate Prediction System</p>
        </div>
    </div>
</body>
</html>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 30px;
        }
        .header {
            text-align: center;
            padding-bottom: 20px;
            border-bottom: 2px solid #17a2b8;
        }
        .header h1 {
            color: #17a2b8;
            margin: 0;
        }
        .content {
            padding: 20px 0;
        }
        .button {
            display: inline-block;
            padding: 12px 30px;
            background-color: #17a2b8;
            color: white !important;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }
        .button:hover {
            background-color: #138496;
        }
        .footer {
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            font-size: 12px;
            color: #666;
        }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .link-box {
            background: #ffffff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            word-break: break-all;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
            <p>Hydrogen Production Rate Prediction System</p>
        </div>

        <div class="content">
            <p>Hello <strong>{{ $user->FullName }}</strong>,</p>

            <p>We received a request to reset the password for your account (<strong>{{ $user->Username }}</strong>).</p>

            <p>Click the button below to reset your password:</p>

            <div style="text-align: center;">
                <a href="{{ $resetUrl }}" class="button">Reset Password</a>
            </div>

            <div class="warning">
                <strong>⚠️ Important:</strong>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>This link will expire in <strong>60 minutes</strong></li>
                    <li>If you didn't request this, please ignore this email</li>
                    <li>Your password will remain unchanged until you create a new one</li>
                </ul>
            </div>

            <p><strong>If the button doesn't work, copy and paste this link into your browser:</strong></p>
            <div class="link-box">
                <a href="{{ $resetUrl }}">{{ $resetUrl }}</a>
            </div>

            <p>If you did not request a password reset, no further action is required.</p>
        </div>

        <div class="footer">
            <p>This is an automated email from Hydrogen MLOps System. Please do not reply to this email.</p>
            <p>&copy; {{ date('Y') }} Hydrogen Production Rate Prediction System. All rights reserved.</p>
        </div>
    </div>
</body>
</html>

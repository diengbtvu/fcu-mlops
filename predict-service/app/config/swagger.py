from flasgger import Swagger

def init_swagger(app):
    """Initialize Swagger UI for the Flask app"""
    
    # Swagger config - use api-docs endpoint only
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api-docs/",
        "swagger_ui_bundle_js": "//unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js",
        "swagger_ui_standalone_preset_js": "//unpkg.com/swagger-ui-dist@3/swagger-ui-standalone-preset.js",
        "jquery_js": "//unpkg.com/jquery@2.2.4/dist/jquery.min.js",
        "swagger_ui_css": "//unpkg.com/swagger-ui-dist@3/swagger-ui.css"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Predict Service API",
            "description": "Machine Learning prediction service for Hydrogen Production Rate (HPR) prediction",
            "contact": {
                "name": "API Support",
                "email": "support@example.com"
            },
            "version": "1.0.0"
        },
        "host": "localhost:5000",
        "basePath": "/",
        "schemes": [
            "http"
        ],
        "consumes": [
            "application/json"
        ],
        "produces": [
            "application/json"
        ],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization", 
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
            }
        },
        "definitions": {
            "PredictRequest": {
                "type": "object",
                "required": [
                    "ph", "vss", "ethanol", "acetate", "propionate", "butyrate",
                    "sucrose_degradation", "orp_mid", "orp_low", "vfa", "cod_o"
                ],
                "properties": {
                    "ph": {
                        "type": "number",
                        "description": "System pH",
                        "example": 6.5
                    },
                    "vss": {
                        "type": "number",
                        "description": "Volatile Suspended Solids (mg/L)",
                        "example": 3500
                    },
                    "ethanol": {
                        "type": "number",
                        "description": "Ethanol concentration (mM)",
                        "example": 12.5
                    },
                    "acetate": {
                        "type": "number",
                        "description": "Acetate concentration (mM)",
                        "example": 25.0
                    },
                    "propionate": {"type": "number", "description": "Propionate concentration (mM)", "example": 8.0},
                    "butyrate": {"type": "number", "description": "Butyrate concentration (mM)", "example": 35.0},
                    "sucrose_degradation": {"type": "number", "description": "Sucrose degradation (%)", "example": 72.0},
                    "orp_mid": {"type": "number", "description": "ORP Mid (mV)", "example": -180.0},
                    "orp_low": {"type": "number", "description": "ORP Low (mV)", "example": -220.0},
                    "vfa": {"type": "number", "description": "VFA concentration (mM)", "example": 90.0},
                    "cod_o": {"type": "number", "description": "COD-O (mg/L)", "example": 12000.0},
                }
            },
            "PredictResponse": {
                "type": "object",
                "properties": {
                    "prediction": {
                        "type": "number",
                        "description": "Predicted Hydrogen Production Rate",
                        "example": 0.8756
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement",
                        "example": "L/h/L"
                    },
                    "user": {
                        "type": "string", 
                        "description": "Username of the requester",
                        "example": "testuser"
                    }
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error message",
                        "example": "Missing field: ph"
                    }
                }
            },
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Service status",
                        "example": "healthy"
                    },
                    "message": {
                        "type": "string",
                        "description": "Status message",
                        "example": "Predict service is running"
                    }
                }
            }
        }
    }
    
    # Create Swagger instance
    swagger = Swagger(app, config=swagger_config, template=swagger_template)
    
    return swagger

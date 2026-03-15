from app import create_app
from app.config.env import Config_env

app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config_env.PORT, debug=True)
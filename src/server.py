import logging
from flask import Flask
from flask_graphql import GraphQLView
from flask_cors import CORS
from api import schema

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

try:
    app.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            graphiql=True  
        )
    )
    logger.info("GraphQL endpoint configured successfully")
except Exception as e:
    logger.error(f"Failed to configure GraphQL endpoint: {e}")
    raise

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "stacktrace-analyzer"}

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {error}")
    return {"error": "Endpoint not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return {"error": "Internal server error"}, 500

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
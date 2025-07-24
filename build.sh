echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p logs data
mkdir -p src/logs src/data

echo "Build completed successfully!"

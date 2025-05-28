cd /build
pip install --target ./package -r requirements-lambda.txt
pip install --target ./package ./wibl-manager
pip install --target ./package --no-deps .

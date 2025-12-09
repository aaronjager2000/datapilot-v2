#!/bin/bash
cd "/Users/aarongrant/datapilot grind/datapilot/backend"
source venv/bin/activate
echo "✅ Venv activated! Python version:"
python --version
echo "✅ Testing config import:"
python -c "from app.core.config import settings; print('Config loaded successfully!')"

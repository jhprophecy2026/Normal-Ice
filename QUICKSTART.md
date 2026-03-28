# Quick Start Guide

## Get Your Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

## Setup & Run (5 minutes)

### 1. Backend Setup

Open a terminal and run:

```bash
# Navigate to backend
cd backend

# Create virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Create virtual environment (macOS/Linux)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key to .env file
# Open backend/.env and replace 'your_gemini_api_key_here' with your actual API key

# Start the backend server
python -m app.main
```

Backend will run at: http://localhost:8000

### 2. Frontend Setup

Open a **NEW terminal** and run:

```bash
# Navigate to frontend
cd frontend

# Install dependencies (first time only)
npm install

# Start the frontend
npm run dev
```

Frontend will run at: http://localhost:5173

### 3. Test the Application

1. Open http://localhost:5173 in your browser
2. You should see "API Connected" status
3. Upload a sample PDF (lab report or prescription)
4. Click "Process Document"
5. View the generated FHIR bundle!

## Troubleshooting

### "API Offline" message
- Make sure backend is running on port 8000
- Check that your Gemini API key is correctly set in `backend/.env`

### Import errors in backend
```bash
cd backend
pip install --upgrade -r requirements.txt
```

### Frontend won't start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### PDF processing fails
- Ensure PDF is not password-protected
- Check PDF file size (max 10MB)
- Verify Gemini API key is valid

## Next Steps

- Try uploading different types of lab reports and prescriptions
- Download the generated FHIR bundles
- Explore the FHIR bundle structure in the JSON viewer
- Check the extracted text to see what the AI read from your PDF

## Need Help?

Refer to the main README.md for detailed documentation.

# Healthcare FHIR MVP - Clinical Data to FHIR Converter

AI-powered system that converts clinical documents (lab reports and prescriptions) from PDF format into standardized FHIR R4 bundles.

## Features

- **PDF Processing**: Extract text from lab reports and prescriptions
- **AI-Powered Extraction**: Uses Gemini 1.5 Pro to intelligently extract structured clinical data
- **FHIR R4 Compliance**: Generates valid FHIR bundles with comprehensive resources
- **Minimalist UI**: Clean, professional interface for easy document processing
- **Real-time Processing**: Fast document processing with visual feedback

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Gemini 1.5 Pro** - Google's LLM for intelligent data extraction
- **pdfplumber & PyMuPDF** - PDF text extraction
- **fhir.resources** - FHIR R4 resource generation

### Frontend
- **React 18** with TypeScript
- **Vite** - Fast build tool
- **Axios** - HTTP client

## Project Structure

```
healthcare-fhir-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration settings
│   │   ├── routes/
│   │   │   └── process.py       # API endpoints
│   │   ├── services/
│   │   │   ├── ocr.py           # PDF text extraction
│   │   │   ├── llm.py           # Gemini LLM integration
│   │   │   └── fhir_mapper.py   # FHIR bundle generation
│   │   └── models/
│   │       └── schemas.py       # Pydantic models
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.tsx   # File upload component
│   │   │   ├── ResultsView.tsx  # Results display
│   │   │   └── JsonViewer.tsx   # JSON viewer
│   │   ├── services/
│   │   │   └── api.ts           # API client
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
│
└── README.md
```

## Setup Instructions

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Gemini API Key** (Get it from [Google AI Studio](https://makersuite.google.com/app/apikey))

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   # Copy the example env file
   cp .env.example .env
   
   # Edit .env and add your Gemini API key
   # GEMINI_API_KEY=your_actual_api_key_here
   ```

5. **Run the backend server**:
   ```bash
   # From the backend directory
   python -m app.main
   
   # Or using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Backend will be available at: `http://localhost:8000`
   API docs at: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   ```

   Frontend will be available at: `http://localhost:5173`

## Usage

1. **Start both backend and frontend servers** (in separate terminals)

2. **Open the application** in your browser at `http://localhost:5173`

3. **Upload a PDF**:
   - Drag and drop a PDF file (lab report or prescription)
   - Or click to browse and select a file

4. **Process the document**:
   - Click "Process Document" button
   - Wait for AI to extract and structure the data

5. **View results**:
   - **Summary Tab**: Overview of generated FHIR resources
   - **FHIR Bundle Tab**: Complete FHIR bundle in JSON format
   - **Extracted Text Tab**: Raw text extracted from PDF

6. **Download**: Use the "Download JSON" button to save the FHIR bundle

## API Endpoints

### Health Check
```
GET /api/health
```
Returns API status and Gemini configuration status.

### Process PDF
```
POST /api/process-pdf
```
**Body**: `multipart/form-data` with PDF file

**Response**:
```json
{
  "success": true,
  "message": "Successfully processed lab_report",
  "document_type": "lab_report",
  "extracted_text": "...",
  "fhir_bundle": { ... }
}
```

## FHIR Resources Generated

### Lab Reports
- **Patient** - Demographics
- **Practitioner** - Ordering physician
- **Organization** - Lab/hospital
- **Observation** - Individual test results
- **DiagnosticReport** - Groups observations
- **Condition** - Diagnosis (if present)

### Prescriptions
- **Patient** - Demographics
- **Practitioner** - Prescriber
- **Organization** - Clinic/hospital
- **Medication** - Medication details
- **MedicationRequest** - Prescription orders
- **Condition** - Diagnosis (if present)

## Configuration

### Backend Configuration (`backend/.env`)
```env
GEMINI_API_KEY=your_api_key
HOST=0.0.0.0
PORT=8000
FRONTEND_URL=http://localhost:5173
```

### Frontend Configuration (`frontend/.env`)
```env
VITE_API_URL=http://localhost:8000/api
```

## Development

### Running Tests
```bash
# Backend (when tests are added)
cd backend
pytest

# Frontend (when tests are added)
cd frontend
npm test
```

### Building for Production

**Backend**:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm run build
npm run preview
```

## Troubleshooting

### Backend Issues

**1. Import errors for dependencies**:
```bash
pip install --upgrade -r requirements.txt
```

**2. Gemini API errors**:
- Verify API key is correctly set in `.env`
- Check API quota at Google AI Studio
- Ensure API key has necessary permissions

**3. PDF extraction fails**:
- Ensure PDF is not password-protected
- Try both text-based and scanned PDFs
- Check PDF file size (max 10MB)

### Frontend Issues

**1. API connection fails**:
- Verify backend is running on port 8000
- Check CORS settings in backend
- Confirm `.env` file has correct API URL

**2. Build errors**:
```bash
rm -rf node_modules package-lock.json
npm install
```

## Limitations (MVP)

- Session-based processing (no database)
- Supports only PDF files
- Limited to lab reports and prescriptions
- No authentication/authorization
- Single file processing at a time

## Future Enhancements

- Database integration for data persistence
- Support for more document types (discharge summaries, imaging reports)
- Batch processing capabilities
- User authentication and multi-tenancy
- Real-time validation with external code systems (LOINC, RxNorm)
- Integration with EHR systems via FHIR APIs
- Advanced analytics and reporting

## License

This project is an MVP for educational and demonstration purposes.

## Support

For issues or questions, please refer to the project documentation or create an issue in the repository.

---

**Built with Gemini 1.5 Pro | FHIR R4 | FastAPI | React**

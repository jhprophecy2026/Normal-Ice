import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

print(f"[OK] API Key found: {api_key[:10]}...")

# Configure Gemini
try:
    genai.configure(api_key=api_key)
    print("[OK] Gemini configured successfully")
except Exception as e:
    print(f"[ERROR] Configuration error: {e}")
    exit(1)

# List available models
print("\n[INFO] Listing available models...\n")
try:
    models = genai.list_models()
    
    generative_models = []
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            generative_models.append(model.name)
            print(f"[OK] {model.name}")
            print(f"     Display Name: {model.display_name}")
            print(f"     Description: {model.description[:80]}...")
            print()
    
    print(f"\n[SUCCESS] Found {len(generative_models)} models that support generateContent")
    
    if generative_models:
        print(f"\n[RECOMMENDED] Model to use: {generative_models[0]}")
        print(f"              (Use this in your config.py)")
    
except Exception as e:
    print(f"[ERROR] Error listing models: {e}")
    exit(1)

# Test generation with the first available model
if generative_models:
    print(f"\n[TEST] Testing generation with {generative_models[0]}...")
    try:
        model = genai.GenerativeModel(generative_models[0])
        response = model.generate_content("Say 'Hello, Gemini is working!'")
        print(f"[SUCCESS] Test successful!")
        print(f"          Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Generation test failed: {e}")

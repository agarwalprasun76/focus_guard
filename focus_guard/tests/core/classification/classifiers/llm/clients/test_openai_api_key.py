import os
from openai import OpenAI

# API key must come from the environment (never commit real keys).
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
    print("Please set it with: set OPENAI_API_KEY=your-api-key-here")
    exit(1)

# Initialize the client
client = OpenAI(api_key=api_key)

try:
    response = client.responses.create(
        model="gpt-4o-mini",
        input="write a haiku about distraction",
        store=True)

    print(response.output_text)
    
except Exception as e:
    print(f"Error: {str(e)}")
    if "Incorrect API key" in str(e):
        print("Please check that your API key is correct and has sufficient credit.")
    elif "Rate limit" in str(e):
        print("Rate limit exceeded. Please try again later.")
    elif "does not exist" in str(e):
        print("The specified model does not exist. Check the model name.")
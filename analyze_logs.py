import os
import openai
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Directory to scan for Python files
directory_to_monitor = r"C:\Users\pf388\OneDrive\Desktop\screenshare2-master/templates"

# Output directory and file
output_directory = r"C:\Users\pf388\OneDrive\Desktop\screenshare2-master\logs"
if not os.path.exists(output_directory):
    print(f"Creating directory: {output_directory}")
    os.makedirs(output_directory)
else:
    print(f"Directory already exists: {output_directory}")

# Function to analyze file content
def analyze_file_content(file_path):
    """Use OpenAI to analyze a single file's content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Call OpenAI API to analyze file content
        response = openai.ChatCompletion.create(
            model="gpt-4",
             messages=[
                {"role": "system", "content": "You are an assistant that analyzes code and suggests improvements or fixes."},
                {"role": "user", "content": f"""Nós estamos com problemas em tais areas:
                1- https://screenshare2-v3.onrender.com/curitiba_user/tela o link que está sendo gerado para compartilhar a nossa trasnmissão 
                não está funcionando de forma global. Nós já tentamos diversas mudanças no nosso arquivo e ainda sem sucesso. Eu gostaria que você 
                analisasse o meu código por possíveis erros e depois nos dê uma possível solução desse código com problema, alterando os campos necessários
                e mostrando o código inteiro com cada alteração.\n\n{content}"""}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        # Extract response from OpenAI API
        analysis = response['choices'][0]['message']['content']

        # Create a timestamped log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_log_file = os.path.join(output_directory, f"analysis_results_{timestamp}.txt")

        # Append the analysis results to the output log file
        with open(output_log_file, 'a', encoding='utf-8') as output_file:
            output_file.write(f"Analysis for {file_path}:\n")
            output_file.write(analysis + "\n\n")

        print(f"Analysis saved for {file_path}")

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")

# Function to check for Python files and analyze them
def check_for_python_files():
    """Scan for Python files in the directory and analyze them."""
    for root, dirs, files in os.walk(directory_to_monitor):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                analyze_file_content(file_path)

# Infinite loop to check the directory at regular intervals
if __name__ == '__main__':
    print(f"Monitoring directory: {directory_to_monitor}")

    # Run the file check loop indefinitely
    while True:
        try:
            check_for_python_files()  # Check for files and analyze them
        except KeyboardInterrupt:
            print("Stopping the script.")
            break  # Exit the loop if the user interrupts (Ctrl+C)

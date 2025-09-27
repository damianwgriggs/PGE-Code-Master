🏗️ Unified AI Architect
An advanced, multi-stage AI application designed to function as a "learning craftsman" for software development. This tool goes beyond simple code generation by integrating a Generator-Critic workflow with a persistent, long-term memory core (RAG) to produce high-quality, multi-file software projects and improve upon its own past work.

✨ Core Concept: The "Learning Craftsman"
The central innovation of this project is the creation of an AI that doesn't just execute a task, but learns from the experience. Most AI code generators are stateless; they give the same or a similar answer to the same prompt every time.

This architect is different. By using a Retrieval-Augmented Generation (RAG) system, it saves every completed project to a local vector database. When given a new prompt, it first consults its "memory" for relevant past work.

This was proven during testing:

First Run: The AI was prompted to build a calculator app. It produced a correct, functional script.

Second Run: After a full restart (clearing all session state), it was given the exact same prompt.

The Result: The AI retrieved its memory of the first successful attempt and proactively improved its own architecture, refactoring the code to use a more efficient and robust design (st.form).

It didn't just recall; it reflected and refined. This is the difference between a simple tool and a digital craftsman.

🚀 Key Features
Dual Generation Modes: Can create both simple Single-File Applications and complex Multi-File Projects.

Multi-Stage Workflow: Utilizes a sophisticated pipeline for high-quality output:

Memory Retrieval: Consults past projects for context.

Architectural Planning: Designs the application or project structure.

Code Generation: Writes the code, file by file.

Critic Analysis: An independent AI agent reviews the code for flaws and relevance.

Final Polish: Integrates the critic's feedback to produce the final version.

Persistent Long-Term Memory: Powered by a local Qdrant vector database, the architect's experience grows with every project it completes.

Interactive UI: Built with Streamlit for a clean, user-friendly interface with process logs and a tabbed display for multi-file code.

Project Download: Generates a .zip archive for easy download of complete multi-file projects.

🛠️ Technology Stack
Frontend: Streamlit

Language Model: Google Gemini 2.0 Flash

Vector Database: Qdrant (running in local, on-disk mode)

Text Embeddings: SentenceTransformers (all-MiniLM-L6-v2)

⚙️ Setup and Installation
Follow these steps to get the Unified AI Architect running on your local machine.

1. Clone the Repository
git clone [https://github.com/your-username/unified-ai-architect.git](https://github.com/your-username/unified-ai-architect.git)
cd unified-ai-architect

2. Create a Virtual Environment
It's highly recommended to use a virtual environment to manage dependencies.

# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

3. Install Dependencies
Install all the required Python packages from the requirements.txt file.

pip install -r requirements.txt

4. Configure Your API Key
Open the app.py file in a text editor and replace the placeholder with your Google AI API key.

# app.py - Line 33
API_KEY = "YOUR_API_KEY_HERE" # Replace with your actual key

5. Run the Application
Once the installation and configuration are complete, run the Streamlit application from your terminal.

streamlit run app.py

The application should now be open and running in your web browser.

📖 How to Use
Select the Mode: In the sidebar, choose whether you want to generate a "Single-File App" or a "Multi-File Project".

Enter Your Prompt: In the chat input at the bottom of the screen, provide a detailed, clear prompt for the application you want to build.

Observe the Process: The "Process Log" will show you each stage of the AI's thought process in real-time, from memory retrieval to the final polish.

Review the Code: The final, generated code will appear in the "Final Application Code" section. For multi-file projects, the code for each file will be displayed in its own tab.

Download Your Project: Click the "Download .py file" or "Download Project .zip" button to save the code to your computer.

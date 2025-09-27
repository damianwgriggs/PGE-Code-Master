# app.py: The main file for the Unified AI Architect application.
# v7.0: True RAG Integration - Long-term context is now plumbed through the entire workflow.

import streamlit as st
import asyncio
import json
import google.generativeai as genai
import zipfile
import io

# --- Core Component Imports ---
from vector_db_manager import VectorDBManager
from memory_processor import save_to_memory_async
from context_manager import ContextManager

# --- 1. Configuration & Setup ---
PROCESS_MEMORY_COLLECTION = "process_memory"

# --- Helper to run asyncio tasks in Streamlit ---
def run_async_task(coro):
    """Runs an asyncio coroutine in the Streamlit event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- 2. Google AI API Configuration ---
# PASTE YOUR GOOGLE AI API KEY HERE.
API_KEY = "APIKEYHERE" # Replace with your actual key

try:
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        st.error("FATAL: Please enter your Google AI API key in the `API_KEY` variable in `app.py`.")
        st.stop()
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error(f"FATAL: Failed to configure Google AI. Error: {e}")
    st.stop()

@st.cache_resource
def get_gemini_client():
    """Initializes and caches the Gemini model."""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        return model
    except Exception as e:
        st.error(f"Failed to initialize Gemini model. Error: {e}")
        st.stop()

# --- 3. The Integrated AI Engine (with True RAG) ---
class IntegratedAIEngine:
    """Orchestrates the entire Generator-Critic workflow."""
    def __init__(self, model: genai.GenerativeModel, db_manager: VectorDBManager):
        self.model = model
        self.db_manager = db_manager

    def _make_llm_request(self, system_prompt, user_prompt, context=""):
        """Generic, reusable function to make a request to the Gemini API, now with RAG context."""
        context_header = f"**Relevant Long-Term Memory (for context and reference):**\n{context}\n\n---\n\n" if context else ""
        full_prompt = f"{context_header}{system_prompt}\n\n---\n\n{user_prompt}"
        
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.4)
            )
            return response.text
        except Exception as e:
            st.error(f"LLM Request failed: {e}")
            return f"Error: LLM request failed. Details: {e}"

    async def retrieve_relevant_context(self, query: str, top_k: int = 3):
        """Searches the vector DB for context relevant to a new query."""
        try:
            results = await self.db_manager.search(
                collection_name=PROCESS_MEMORY_COLLECTION,
                query_text=query,
                limit=top_k
            )
            if not results: return ""
            
            context_str = "\n\n---\n\n".join([
                f"Relevant Past Artifact (Score: {res['score']:.2f}):\nType: {res['payload'].get('type', 'N/A')}\nContent:\n{res['payload'].get('text', 'N/A')}"
                for res in results
            ])
            return context_str
        except Exception as e:
            st.warning(f"Could not retrieve context from memory: {e}")
            return ""

    # --- SINGLE-FILE WORKFLOW ---
    def architect_planning_single_file(self, master_prompt, context):
        system_prompt = "You are a world-class software architect. Your task is to break down a user's prompt for a SINGLE-FILE application into a step-by-step plan. Use the provided long-term memory for reference."
        user_prompt = f"**Current Project Request:**\n{master_prompt}\n\n---\n\nPlease create the new step-by-step development plan for a single file."
        response_text = self._make_llm_request(system_prompt, user_prompt, context)
        if response_text.startswith("Error:"): return None
        plan_steps = [line.strip() for line in response_text.split('\n') if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))]
        if not plan_steps: 
            st.error("The planning stage failed to produce a valid step-by-step list.")
            st.text_area("Model Response to Debug", response_text, height=200)
            return None
        return [{"section_name": f"Step {i+1}", "description": step} for i, step in enumerate(plan_steps)]

    def architect_generation_loop(self, plan, master_prompt, context):
        all_code_blocks = []
        for i, step in enumerate(plan):
            section_name = step.get("section_name", f"Part {i+1}")
            description = step.get("description", "")
            system_prompt = "You are an expert programmer. Write a block of code for a specific section of a larger script. Use the provided long-term memory for reference on style and structure. CRITICAL RULES: 1. ONLY output the raw code. 2. Do NOT include explanations or markdown."
            user_prompt = f"**Full Project Brief:**\n{master_prompt}\n---\n**Current Task:** `{section_name}`\n**Instructions:** {description}"
            generated_code = self._make_llm_request(system_prompt, user_prompt, context)
            if generated_code.startswith("Error:"): return None
            clean_code = generated_code.strip().replace("```python", "").replace("```", "").strip()
            all_code_blocks.append(f"# --- {section_name.upper()} ---\n{clean_code}\n")
        return "\n".join(all_code_blocks)

    def architect_self_correction(self, generated_code, master_prompt, context):
        system_prompt = "You are a Senior Software Engineer performing a final code review. Refine the provided script to perfection, using the provided long-term memory as a style guide. CRITICAL RULES: 1. Correct any bugs. 2. Ensure 100% compliance with the prompt. 3. Your final output MUST be ONLY the raw, complete, corrected code."
        user_prompt = f"**Original Prompt:**\n{master_prompt}\n---\n**Script to Correct:**\n```python\n{generated_code}\n```"
        corrected_code = self._make_llm_request(system_prompt, user_prompt, context)
        if corrected_code.startswith("Error:"): return generated_code
        return corrected_code.strip().replace("```python", "").replace("```", "").strip()

    # --- MULTI-FILE WORKFLOW ---
    def plan_multi_file_structure(self, master_prompt, context):
        system_prompt = """You are a lead software architect planning a multi-file project. Define the file structure based on the user's request, using long-term memory for reference.
CRITICAL: Respond with ONLY a JSON object. The JSON should have a single key "files" which is a list of objects, each with "filename" and "description" keys."""
        user_prompt = f"**Current Project Request:**\n{master_prompt}\n\n---\n\nGenerate the JSON file structure."
        response_text = self._make_llm_request(system_prompt, user_prompt, context)
        if response_text.startswith("Error:"): return None
        try:
            clean_json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
            return json.loads(clean_json_str)
        except json.JSONDecodeError:
            st.error("Multi-file planning failed to produce valid JSON.")
            st.text_area("Model Response to Debug", response_text, height=200)
            return None

    def generate_multi_file_loop(self, file_plan, master_prompt, context):
        project_code = {}
        files_to_generate = file_plan.get("files", [])
        if not files_to_generate: return None

        for file_info in files_to_generate:
            filename = file_info.get("filename")
            description = file_info.get("description")
            if not filename or not description: continue

            system_prompt = "You are an expert programmer writing a single file for a larger project. Use the long-term memory for context on how this file should interact with others. CRITICAL RULES: 1. ONLY output the raw code. 2. Do NOT add explanations."
            user_prompt = (f"**Full Project Brief:**\n{master_prompt}\n---\n"
                           f"**Current File to Generate:** `{filename}`\n"
                           f"**File's Purpose:** {description}")
            
            generated_code = self._make_llm_request(system_prompt, user_prompt, context)
            if generated_code.startswith("Error:"):
                project_code[filename] = f"# ERROR: Failed to generate code.\n# Details: {generated_code}"
            else:
                project_code[filename] = generated_code.strip().replace("```python", "").replace("```", "").strip()
        
        return project_code

    # --- SHARED WORKFLOW STEPS ---
    def critic_analysis(self, generated_code, master_prompt, context):
        code_str = "\n".join(f"# FILE: {fn}\n{co}" for fn, co in generated_code.items()) if isinstance(generated_code, dict) else generated_code
        system_prompt = """You are a Senior Software Engineer on code review. Your FIRST priority is to check if the script's purpose matches the user's prompt. If not, state this. If it matches, identify ONE meaningful improvement. Use long-term memory for context."""
        user_prompt = f"**User's Original Prompt:**\n{master_prompt}\n\n---\n\n**Script(s) for your review:**\n\n```python\n{code_str}\n```"
        return self._make_llm_request(system_prompt, user_prompt, context)

    def final_polish(self, code, feedback, master_prompt, context):
        code_str = "\n".join(f"# FILE: {fn}\n{co}" for fn, co in code.items()) if isinstance(code, dict) else code
        system_prompt = "You are a Senior Software Engineer. Integrate the following feedback into the provided code. Use long-term memory for context. CRITICAL: Your output MUST be ONLY the raw, complete, corrected code. For multi-file projects, use '# FILE: filename.py' headers."
        user_prompt = (f"**Original Prompt:**\n{master_prompt}\n---\n"
                       f"**Your Code:**\n```python\n{code_str}\n```\n---\n"
                       f"**Feedback to Incorporate:**\n{feedback}")
        return self._make_llm_request(system_prompt, user_prompt, context)

# --- 4. Streamlit UI & Application Flow ---
st.set_page_config(layout="wide", page_title="Unified AI Architect")
st.title("🏗️ Unified AI Architect")
st.markdown("An integrated AI architect with long-term memory (RAG) and multi-file project capabilities.")

if 'db_manager' not in st.session_state:
    st.session_state.db_manager = VectorDBManager()
    run_async_task(st.session_state.db_manager.initialize_collection(PROCESS_MEMORY_COLLECTION))
if 'ai_engine' not in st.session_state:
    model = get_gemini_client()
    st.session_state.ai_engine = IntegratedAIEngine(model, st.session_state.db_manager)
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'final_code' not in st.session_state:
    st.session_state.final_code = ""

with st.sidebar:
    st.header("⚙️ Controls")
    generation_mode = st.radio("Select Generation Mode:", ("Single-File App", "Multi-File Project"), horizontal=True)
    if st.button("Clear History & Memory", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.final_code = ""
        run_async_task(st.session_state.db_manager.delete_collection(PROCESS_MEMORY_COLLECTION))
        st.rerun()
    st.header("📝 Chat History")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

col1, col2 = st.columns(2)
with col1:
    st.subheader("Process Log")
    log_container = st.container(height=600)
with col2:
    st.subheader("Final Application Code")
    code_container = st.container(height=600)

if prompt := st.chat_input("Enter your detailed prompt..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt, "is_saved": False})
    
    with log_container:
        with st.status(f"Initiating AI Architect in {generation_mode} mode...", expanded=True) as status:
            engine = st.session_state.ai_engine
            db_manager = st.session_state.db_manager
            
            run_async_task(save_to_memory_async(prompt, {"type": "user_prompt", "mode": generation_mode}, db_manager, PROCESS_MEMORY_COLLECTION))

            status.update(label="Step 1: Consulting long-term memory...")
            context = run_async_task(engine.retrieve_relevant_context(prompt))
            if context:
                st.markdown("### Memory Retrieval\n" + context)
            else:
                st.markdown("### Memory Retrieval\nNo relevant memories found.")

            if generation_mode == "Single-File App":
                status.update(label="Step 2: Architectural Planning...")
                plan = engine.architect_planning_single_file(prompt, context)
                if not plan: st.error("Planning failed."); st.stop()
                plan_text = "\n".join([step['description'] for step in plan])
                st.markdown("### Development Plan\n" + plan_text)
                run_async_task(save_to_memory_async(plan_text, {"type": "architect_plan"}, db_manager, PROCESS_MEMORY_COLLECTION))

                status.update(label="Step 3: Generating initial code...")
                v1_code = engine.architect_generation_loop(plan, prompt, context)
                if not v1_code: st.error("Initial generation failed."); st.stop()
                run_async_task(save_to_memory_async(v1_code, {"type": "v1_code"}, db_manager, PROCESS_MEMORY_COLLECTION))

                status.update(label="Step 4: Performing self-correction...")
                v2_code = engine.architect_self_correction(v1_code, prompt, context)
                run_async_task(save_to_memory_async(v2_code, {"type": "v2_code"}, db_manager, PROCESS_MEMORY_COLLECTION))
                
                status.update(label="Step 5: Submitting for external review...")
                feedback = engine.critic_analysis(v2_code, prompt, context)
                st.markdown("**Critic Feedback:**\n" + feedback)
                run_async_task(save_to_memory_async(feedback, {"type": "critic_feedback"}, db_manager, PROCESS_MEMORY_COLLECTION))

                status.update(label="Step 6: Applying final polish...")
                final_code = engine.final_polish(v2_code, feedback, prompt, context)
            
            else: # Multi-File Project
                status.update(label="Step 2: Planning multi-file structure...")
                file_plan = engine.plan_multi_file_structure(prompt, context)
                if not file_plan: st.error("Multi-file planning failed."); st.stop()
                plan_text = json.dumps(file_plan, indent=2)
                st.markdown("### Project File Structure\n```json\n" + plan_text + "\n```")
                run_async_task(save_to_memory_async(plan_text, {"type": "multi_file_plan"}, db_manager, PROCESS_MEMORY_COLLECTION))
                
                status.update(label="Step 3: Generating code for all files...")
                v1_code = engine.generate_multi_file_loop(file_plan, prompt, context)
                if not v1_code: st.error("Multi-file generation failed."); st.stop()
                run_async_task(save_to_memory_async(json.dumps(v1_code), {"type": "v1_code_multifile"}, db_manager, PROCESS_MEMORY_COLLECTION))

                status.update(label="Step 4: Submitting project for external review...")
                feedback = engine.critic_analysis(v1_code, prompt, context)
                st.markdown("**Critic Feedback:**\n" + feedback)
                run_async_task(save_to_memory_async(feedback, {"type": "critic_feedback_multifile"}, db_manager, PROCESS_MEMORY_COLLECTION))

                status.update(label="Step 5: Applying final polish to project...")
                final_code = engine.final_polish(v1_code, feedback, prompt, context)

            run_async_task(save_to_memory_async(json.dumps(final_code) if isinstance(final_code, dict) else final_code, {"type": "final_code"}, db_manager, PROCESS_MEMORY_COLLECTION))
            st.session_state.final_code = final_code
            status.update(label="✔ Process Complete!", state="complete")

    assistant_response = f"I have completed the code generation process for the **{generation_mode}**. The final result is now available."
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_response, "is_saved": False})
    
    context_mgr = ContextManager(st.session_state.chat_history)
    overflow = context_mgr.get_overflow_chunks()
    if overflow:
        for chunk in overflow:
            run_async_task(save_to_memory_async(chunk['content'], {"type": "chat_history", "role": chunk['role']}, db_manager, PROCESS_MEMORY_COLLECTION))
    st.rerun()

with code_container:
    if st.session_state.final_code:
        if isinstance(st.session_state.final_code, str):
            st.code(st.session_state.final_code, language='python', line_numbers=True)
            st.download_button("💾 Download .py file", st.session_state.final_code, "generated_app.py", "text/python")
        
        elif isinstance(st.session_state.final_code, dict):
            # ... (Multi-file display and zip download logic) ...
            keys = list(st.session_state.final_code.keys())
            if keys:
                file_tabs = st.tabs(keys)
                for i, filename in enumerate(keys):
                    with file_tabs[i]:
                        st.code(st.session_state.final_code[filename], language='python', line_numbers=True)
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, code in st.session_state.final_code.items():
                        # Handle potential parsing issues from final polish
                        if code.strip().startswith("# FILE:"):
                            # This is a fallback if the polish step returns a single string
                            # A more robust implementation would parse this string properly
                            st.warning("Final polish returned a single string for a multi-file project. Displaying raw output.")
                            zip_file.writestr("polished_output.txt", code)
                            break
                        zip_file.writestr(filename, code)
                zip_buffer.seek(0)
                st.download_button("💾 Download Project .zip", zip_buffer, "generated_project.zip", "application/zip")
    else:
        st.info("Your generated code will appear here.")


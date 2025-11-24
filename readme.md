# AI Interview Partner

This project implements a multi-step, voice-enabled web application that conducts mock job interviews. It uses the Google Gemini API to serve as a professional interviewer, providing challenging questions based on the user's selected **Role, Level, and Interview Type (Technical, Managerial, or HR/Behavioral)**, and provides a comprehensive feedback report at the end.

## ✨ Key Features

* **Multi-Step Setup:** Guided user setup to select Domain, Role, Level, and Interview Type.
* **Voice Input/Output:** Interviewer questions are read aloud using Text-to-Speech (TTS). Candidate answers can be provided via microphone (Speech-to-Text, STT).
* **Persona Customization:** The AI adopts a strict, professional persona focused on the selected interview type.
* **Adaptive Interviewing:** The AI generates challenging follow-up questions if the candidate's answers are vague or lack structure.
* **Structured Feedback:** Generates a final report with an overall score, technical analysis, communication review, and actionable next steps.

## 🛠️ Architecture and Design Decisions

The application follows a standard **Python/Flask monolithic architecture** to manage user sessions and interact with the Gemini API. 

### Backend (Python/Flask)

* **State Management:** Flask's built-in **`session`** object is used to securely store multi-step user inputs (`role`, `level`, `interview_type`) and the entire conversation history (`chat_history` for display, `gemini_chat_history_parts` for API continuation).
* **Gemini API:** The `google-genai` SDK is used in a **Chat Session** (`client.chats.create`). A persistent `system_instruction` (the **System Prompt**) is used to enforce the strict interviewing persona and rules across multiple turns.
* **Robustness:** Aggressive **regex cleaning** is applied to the initial AI response to filter out invisible SSML/noise tokens that can cause voice artifacts ("speaker high volume play" or "play").
* **Interview Type:** The chosen type (`Technical`, `HR/Behavioral`, etc.) is injected into the System Prompt to dynamically steer the model's question generation.

### Frontend (HTML/CSS/JavaScript)

* **UI/UX:** A responsive, multi-step interface (`setup.html`) guides the user through the configuration process.
* **Voice Features (Client-Side):**
    * **TTS:** Handled by the **Web Speech API (SpeechSynthesis)** in JavaScript, with a manual "Play" button fallback for the first message to bypass browser autoplay restrictions.
    * **STT:** Handled by the **Web Speech API (webkitSpeechRecognition)**, allowing users to speak their answers.

## 🚀 Setup Instructions

### Prerequisites

1.  **Python 3.8+**
2.  **A Gemini API Key** (Get one from Google AI Studio)

### Step-by-Step Installation

1.  **Clone the Repository:**
    ```bash
    git clone (https://github.com/aditi-nadiger/AI-Agent-Projecy-.git)
    cd AI-Agent-Project
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Your API Key:**
    Set the environment variable with your Gemini API Key.
    ```bash
    # Linux/macOS
    export GEMINI_API_KEY="YOUR_API_KEY"
    
    # Windows (CMD)
    set GEMINI_API_KEY="YOUR_API_KEY"
    ```

4.  **Run the Application:**
    ```bash
    python app.py
    ```
    The application will start on `http://127.0.0.1:5000/`.


5.  **Start Interview:** Open your browser to the provided address and follow the setup steps.

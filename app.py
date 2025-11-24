import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from google import genai
from google.genai import types
import re 

# --- 1. CONFIGURATION AND INITIALIZATION ---
app = Flask(__name__)
# CRITICAL: Set a secret key for session management (e.g., in a real app, use os.urandom(24))
app.secret_key = 'a_very_secret_key_for_session_management' 

# Check for API Key at startup
if 'GEMINI_API_KEY' not in os.environ:
	print("FATAL: Please set the GEMINI_API_KEY environment variable.")
	# In a production setting, this should throw an error or handle gracefully
	exit()

try:
	client = genai.Client()
	MODEL_NAME = 'gemini-2.5-flash'
except Exception as e:
	print(f"Error initializing Gemini client: {e}")
	exit()

# --- 2. THE SYSTEM PROMPTS (THE AGENT'S BRAIN) ---
def get_system_prompt(role: str, level: str, interview_type: str) -> str:
    """Defines the AI's persona and rules for the interview phase."""
    interviewer_name = "AI Interviewer"
    return f"""
    You are an extremely professional and challenging **{level} {role}** interviewer.
    Your name is {interviewer_name}. Do not mention this name in the interview unnecessarily.
    The primary focus of this interview is **{interview_type}**.
    Your task is to conduct a focused, multi-turn mock job interview.

    **Your Rules:**
    1. Ask only **one question at a time**, focused on the {interview_type} domain.
    2. Maintain a professional, conversational, and strict tone.
    3. **CRITICAL:** All responses must use **perfect grammar, correct spelling, and proper punctuation (including apostrophes, commas, and periods).**
    4. If the user's previous answer was vague, lacked specific details, or did not use a proper structure (like STAR for behavioral questions), you MUST ask a challenging follow-up question.
    5. If the answer is sufficient, proceed to the next, distinct, core interview question.
    6. Do NOT provide feedback until the user explicitly says 'END INTERVIEW'.
    7. Begin the interview now with a Warm welcome and your first question.
    """



FEEDBACK_PROMPT = """
--- END OF INTERVIEW ---
Your new task is to act as a **Senior HR Analyst**. Analyze the following full interview transcript.

**Provide your detailed, structured feedback in the following four sections ONLY:**
1. **Overall Impression (Score 1-5):** Give a brief summary and a confidence score (e.g., 4/5).
2. **Technical/Role Knowledge:** Identify 2-3 strongest and weakest areas related to the job's core skills.
3. **Communication and Clarity:** Evaluate the use of structured answers (e.g., STAR method) and overall clarity. Cite a specific example of good and bad communication.
4. **Actionable Next Steps:** List 3 clear, practical improvements the candidate should focus on.
"""
# --- 3. FLASK ROUTES AND API LOGIC ---

@app.route('/', methods=['GET', 'POST'])
def setup_interview():
	"""Multi-step setup page to collect domain, role, level, and interview type."""
	# Define all possible roles and interview types
	DOMAINS = {
		"Tech & IT": ["Software Engineer", "Data Scientist", "Cloud Architect"],
		"Business & Sales": ["Sales Manager", "Marketing Analyst", "Business Development"],
		"Healthcare": ["Nurse Practitioner", "Medical Assistant"],
		"Finance": ["Financial Analyst", "Accountant"],
		"Education": ["High School Teacher", "University Lecturer"],
		"Retail & Hospitality": ["Retail Associate", "Restaurant Manager"],
		"Creative & Design": ["UX/UI Designer", "Graphic Artist"],
		"Engineering": ["Mechanical Engineer", "Civil Engineer"],
	}
	INTERVIEW_TYPES = ["Technical", "Managerial", "HR/Behavioral"]

	if request.method == 'POST':
		# Step 1: Domain Selection (or Step 2/3 submission)
		if 'step' in request.form:
			step = int(request.form['step'])
			if step == 1:
				session['domain'] = request.form['domain']
				return render_template('setup.html', step=2, domains=DOMAINS, current_domain=session['domain'])
			elif step == 2:
				session['role'] = request.form['role'].strip()
				session['level'] = request.form['level'].strip()
				return render_template('setup.html', step=3, interview_types=INTERVIEW_TYPES)
			elif step == 3:
				# Final step: Start the interview
				session['interview_type'] = request.form['interview_type']
				session['interview_active'] = True
				# --- START FIX: Initialize Chat and First Question HERE (Moved from /interview) ---
				# 1. Get System Prompt
				system_prompt = get_system_prompt(
					session['role'],
					session['level'],
					session['interview_type']
				)
				# 2. Get the initial question
				initial_chat = client.chats.create(
					model=MODEL_NAME,
					config=types.GenerateContentConfig(
						system_instruction=system_prompt
					),
				)
				
				initial_response = initial_chat.send_message("Start the interview.")
				interviewer_text = initial_response.text

				# --- START FIX: Safer Cleaning to retain grammar/apostrophes ---
				# 1. Targeted removal of voice noise (using broader regex to catch invisible characters)
				noise_pattern = r"(speaker\s*high\s*volume\s*play|speaker\s*high\s*volume|high\s*volume\s*play|play\s*$)"
				interviewer_text = re.sub(noise_pattern, '', interviewer_text, flags=re.IGNORECASE).strip()

				# 2. **CRITICAL:** Allow apostrophes (ASCII 39) which are essential for contractions like I'm, it's.
				# We also remove non-printable ASCII characters (like the SSML remnant)
				interviewer_text = "".join(c for c in interviewer_text if c.isprintable() or c == "'").strip()

				# 3. Final cleanup and formatting
				clean_text = interviewer_text.replace("..", ".").replace(",.", ".").strip()
				clean_text = re.sub(r'\s+', ' ', clean_text).strip() # Clean up residual double spacing

				if not clean_text.endswith(('.', '?', '!')):
					clean_text += "."

				interviewer_text = clean_text
				interviewer_text = interviewer_text.replace('.', '<break time="500ms"/>')
				interviewer_text = interviewer_text.replace('?', '<break time="600ms"/>') 
				# Final cleanup and formatting
				clean_text = clean_text.replace("..", ".").replace(",.", ".").strip()
				clean_text = re.sub(r'\s+', ' ', clean_text).strip()
				if not clean_text.endswith(('.', '?', '!')):
					clean_text += "."
				interviewer_text = clean_text # Use the fully cleaned text
				# 4. Store the initial history parts (for chat continuation)
				history_for_session = []
				for msg in initial_chat.get_history():
					if msg.role != 'system':
						# CRITICAL: Store the *cleaned* text for the AI's first response
						text_to_store = interviewer_text if msg.role == 'model' else "".join(p.text for p in msg.parts)
						history_for_session.append({
							"role": msg.role,
							"parts": [{"text": text_to_store}]
						})
				session['gemini_chat_history_parts'] = history_for_session
				# 5. Store the user-friendly conversation history for display
				# Initializing with the clean first question
				session['chat_history'] = [{"user": "Interviewer", "text": interviewer_text}]
				# --- END FIX: Initialization moved ---
				return redirect(url_for('start_interview'))
		# Initial POST request from Step 1 (fallback logic)
		elif 'domain' in request.form:
			session['domain'] = request.form['domain']
			return render_template('setup.html', step=2, domains=DOMAINS, current_domain=session['domain'])
	# Initial GET request: Show Step 1
	return render_template('setup.html', step=1, domains=DOMAINS)


@app.route('/interview')
def start_interview():
	"""Starts the interview, ensuring setup is complete, and renders the interview page."""
	# CRITICAL: Ensure all required setup variables are present
	required_keys = ['role', 'level', 'interview_type', 'chat_history', 'gemini_chat_history_parts']
	for key in required_keys:
		if key not in session:
			# If any key is missing, redirect to the start of the setup
			return redirect(url_for('setup_interview'))
	# The chat history and first question are now pre-loaded from setup_interview route.
	# Final Render
	return render_template('index.html',
						  role=session['role'],
						  level=session['level'],
						  history=session['chat_history'],
						  active=session.get('interview_active', True))


@app.route('/send_message', methods=['POST'])
def send_message():
	"""Handles sending user message and receiving AI response."""
	# CRITICAL: Check for history before proceeding
	if 'gemini_chat_history_parts' not in session or not session.get('interview_active', False):
		return jsonify({"error": "Interview has ended or session invalid. Please refresh to start a new interview."}), 400
	user_input = request.json.get('message', '').strip()
	if not user_input:
		return jsonify({"error": "Please provide a response."}), 400
	# Append user's message to the display history
	session['chat_history'].append({"user": "Candidate", "text": user_input})
	# 1. Re-initialize the chat session with the full history
	system_prompt = get_system_prompt(
		session['role'],
		session['level'],
		session['interview_type']
	)
	# Convert stored JSON parts back to Content objects
	history_contents = []
	for msg in session['gemini_chat_history_parts']:
		parts = []
		for part in msg['parts']:
			# This is the corrected, simple way to create a text part
			parts.append(types.Part.from_text(text=part['text']))
		history_contents.append(types.Content(role=msg['role'], parts=parts))
	chat = client.chats.create(
		model=MODEL_NAME,
		history=history_contents,
		config=types.GenerateContentConfig(
			system_instruction=system_prompt
		),
	)
	# 2. Check for end command
	if user_input.upper() == 'END INTERVIEW':
		session['interview_active'] = False
		# Get the full transcript for feedback generation
		# NOTE: We include the user's END INTERVIEW message in the transcript for clarity
		transcript = []
		for msg in session['chat_history']:
			# Use the actual role name for the transcript
			role_name = "User" if msg["user"] == "Candidate" else "Interviewer"
			transcript.append(f"({role_name}): {msg['text']}")
		full_transcript = "\n".join(transcript)
		full_prompt_for_feedback = FEEDBACK_PROMPT + "\n\nTranscript:\n" + full_transcript
		# Generate feedback
		feedback_response = client.models.generate_content(
			model=MODEL_NAME,
			contents=[full_prompt_for_feedback]
		)
		session['chat_history'].append({"user": "System", "text": feedback_response.text})
		# Clear the chat history parts to prevent reuse
		session['gemini_chat_history_parts'] = []
		return jsonify({
			"response": feedback_response.text,
			"is_feedback": True
		})
	# 3. Send user's message and get AI's next question/follow-up
	response = chat.send_message(user_input)
	# 4. Update the chat history parts with the new messages
	# Fetch the entire history *after* the send_message call
	new_history_parts = [
		{"role": msg.role, "parts": [{"text": part.text} for part in msg.parts]}
		for msg in chat.get_history()
		if msg.role != 'system'
	]
	session['gemini_chat_history_parts'] = new_history_parts
	# Append AI's response to the display history
	session['chat_history'].append({"user": "Interviewer", "text": response.text})
	# Save session changes
	session.modified = True
	return jsonify({
		"response": response.text,
		"is_feedback": False
	})


if __name__ == "__main__":
	# Ensure the templates directory exists
	os.makedirs('templates', exist_ok=True)
	# Run the Flask app
	app.run(debug=True)
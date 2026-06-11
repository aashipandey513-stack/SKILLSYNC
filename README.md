---
title: SKILLSYNC 2
emoji: 👁
colorFrom: red
colorTo: green
sdk: docker
pinned: false
license: mit
---
# 🚀 SKILLSYNC: AI-Powered Interview Preparation & Soft Skill Evaluator

**SKILLSYNC** is an advanced, AI-driven web framework designed to automate and personalize the interview preparation process. By leveraging a composite pipeline of specialized transformer models, SKILLSYNC provides real-time, actionable feedback to help users master their soft skills and technical communication.

---

## ✨ Key Features
- **Real-Time Acoustic Transcription:** Utilizes OpenAI's Whisper model to accurately transcribe spoken responses during practice interviews.
- **Context-Aware Generative Feedback:** Employs Google's FLAN-T5 to analyze answers and provide constructive, human-like feedback on content and delivery.
- **Quantitative Classification:** Uses Facebook's BART for zero-shot classification to score responses based on specific soft-skill metrics (e.g., confidence, clarity).
- **High-Performance Architecture:** Built on a FastAPI monolithic backend with asynchronous MongoDB persistence, ensuring ultra-low latency processing for a seamless user experience.
- **Modern User Interface:** A highly responsive front-end built with React.js and styled with Tailwind CSS.

---

## 🛠️ Tech Stack
**Frontend:**
- React.js
- Tailwind CSS

**Backend & Database:**
- Python (FastAPI)
- MongoDB (Asynchronous Persistence)

**AI & Machine Learning Pipeline:**
- **OpenAI Whisper:** Acoustic transcription
- **Google FLAN-T5:** Generative feedback
- **Facebook BART:** Zero-shot classification

---

## ⚙️ Architecture Overview
SKILLSYNC operates on a streamlined pipeline designed for speed and accuracy:
1. **Input:** User records an interview response via the React frontend.
2. **Processing:** The audio is sent to the FastAPI backend and instantly transcribed by Whisper.
3. **Analysis:** The text is simultaneously processed by FLAN-T5 (for qualitative feedback) and BART (for quantitative scoring).
4. **Output:** Comprehensive, personalized results are stored in MongoDB and instantly displayed to the user.

---

## 👨‍💻 Author
**Aashi Pandey**
- **LinkedIn:** [(https://linkedin.com/in/aashi-pandey-9a995137b)]
- **GitHub:** [(https://github.com/aashipandey513-stack)]
- **Portfolio/LeetCode:** [(https://leetcode.com/u/aashipandey513-code/)]

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

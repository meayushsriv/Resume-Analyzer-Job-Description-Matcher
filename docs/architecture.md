You must provide a Gemini API key to run the project.

Copy the example file: (For Windows CMD)

Bash

copy .env.example .env
(For macOS/Linux/Git Bash)

Bash

cp .env.example .env
Open the .env file and paste your Gemini API Key:

Ini, TOML

# ... (all the other settings) ...

# --- AI Model API Keys ---
GEMINI_API_KEY="AIzaSy...your...key...here"
3. Run the Application
This 3-step process ensures a clean build that installs all system dependencies (like Tesseract) and creates the database schema correctly.

Step 1: Stop and Delete Old Data

Bash

docker compose -f docker/docker-compose.yml down -v
Step 2: Force a Fresh Rebuild (This will take a few minutes as it installs Tesseract and all Python packages)

Bash

docker compose -f docker/docker-compose.yml build --no-cache
Step 3: Start the Application

Bash

docker compose -f docker/docker-compose.yml up
4. Test Your API
The API documentation is now live at: http://localhost:8000/docs


---

### 2. The Architecture Document

This file explains *how* your system works.

**Create this file:** `/docs/architecture.md`
**Paste this content:**

```markdown
# System Architecture

This project uses an asynchronous, microservice-oriented architecture to handle long-running tasks like OCR and AI analysis without blocking the main API.

## Core Components

1.  **FastAPI (`api`)**: The main web server. It handles all HTTP requests, validates input, creates an initial "pending" job in the database, and pushes the job ID to the Redis queue. It also serves the final JSON data.

2.  **Redis (`redis`)**: The message broker. It holds the queue of tasks for the worker to process.

3.  **Celery Worker (`worker`)**: A separate background process that constantly listens to the Redis queue. When a new job appears, it:
    * Updates the job status in the database to "processing".
    * Pulls the file from the shared volume.
    * Parses the text (using `pdfplumber`, `docx`, or `tesseract` for OCR).
    * Calls the Gemini Pro API with the text and a structured-output schema.
    * Saves the resulting JSON to the database.
    * Updates the job status to "completed".

4.  **PostgreSQL Database (`db`)**: The persistent database that stores all metadata, raw text, and the final structured JSON from the AI.

## Data Flow (On Resume Upload)

1.  User `POSTS` a file to `/api/v1/resumes/upload`.
2.  **FastAPI** receives it, creates a "pending" row in **PostgreSQL**.
3.  **FastAPI** sends a job with the new resume ID to the **Redis** queue.
4.  **FastAPI** immediately returns a `200 OK` with the `resume_id` and "pending" status.
5.  The **Celery Worker** picks up the job from **Redis**.
6.  `worker` updates the status to "processing".
7.  `worker` parses the file text (including OCR if needed).
8.  `worker` sends the text to the **Gemini Pro API**.
9.  `worker` receives the structured JSON from Gemini.
10. `worker` saves the JSON to **PostgreSQL** and marks the status as "completed".
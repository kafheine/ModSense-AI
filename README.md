# ModSense - AI Community Platform

## Folder structure

```text
backend/
    app.py
    db.py
    requirements.txt

frontend/
    index.html
    admin/
        admin-dashboard.html
        analytics.html
        community-management.html
        content-moderation.html
        user-management.html
    auth/
        login.html
        signup.html
    css/
        style.css
    js/
        admin.js
        auth.js
        script.js
    user/
        ai-assistant.html
        community-details.html
        community-feed.html
        community-home.html
        create-post.html
        explore-community.html
        my-communities.html
        post-details.html
        view-community.html

database/
    data.sql
```

## Main changes

- Kept the original folder pattern.
- Removed duplicate SQL dump files and redundant frontend versions.
- Added one consistent Flask backend.
- Added AI moderation when a post is created.
- Added administrator AI re-analysis.
- Added approve/remove moderation actions.
- Added a chatbot page and backend endpoint.
- Added AI chat logging.
- Removed the exposed AI API key from the source code.
- The external AI integration is optional; a local fallback works without a key.

## Setup

1. Create the `modsense_db` database by running `database/data.sql` in MySQL.
2. Open a terminal in `backend`.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set your database password if it is different from the value in `backend/db.py`.
5. Optional: set the AI provider key:

Windows CMD:

```cmd
set GROK_API_KEY=YOUR_KEY
```

PowerShell:

```powershell
$env:GROK_API_KEY="YOUR_KEY"
```

Optional variables:

```text
GROK_API_URL
GROK_MODEL
DB_HOST
DB_USER
DB_PASSWORD
DB_NAME
```

6. Run:

```bash
python app.py
```

7. Open:

```text
http://127.0.0.1:5000/
```

## Important

The project currently keeps the original simple password-storage approach from the supplied project so that it remains compatible with the supplied database design. For a production application, passwords should be hashed and authentication should use proper sessions/tokens.

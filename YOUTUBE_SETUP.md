# YouTube API Setup Guide

To enable automated YouTube uploads, you need to provide a **Google OAuth 2.0 Client Secret** file. This allows the application to upload videos to your channel on your behalf.

## Step 1: Create a Project
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click the project dropdown (top left) and select **"New Project"**.
3.  Name it "ClipCut" (or anything you like) and click **Create**.

## Step 2: Enable YouTube API
1.  In the sidebar, go to **APIs & Services > Library**.
2.  Search for **"YouTube Data API v3"**.
3.  Click it and then click **Enable**.

## Step 3: Configure Consent Screen
1.  In the sidebar, go to **APIs & Services > OAuth consent screen**.
2.  Select **External** (unless you have a G-Suite organization) and click **Create**.
3.  **App Information**:
    *   **App name**: ClipCut Uploader
    *   **User support email**: Select your email.
    *   **Developer contact information**: Enter your email.
4.  Click **Save and Continue** through the "Scopes" section (no changes needed yet).
5.  **Test Users**:
    *   Click **Add Users**.
    *   Enter the **Google/YouTube email address** you want to upload to.
    *   *Note: In "Testing" mode, only added users can authorize the app.*
6.  Click **Save and Continue** and then **Back to Dashboard**.

## Step 4: Create Credentials
1.  In the sidebar, go to **APIs & Services > Credentials**.
2.  Click **+ CREATE CREDENTIALS** (top) and select **OAuth client ID**.
3.  **Application type**: Select **Desktop app**.
4.  **Name**: "ClipCut Client" (default is fine).
5.  Click **Create**.

## Step 5: Download & Place File
1.  You will see a "OAuth client created" popup.
2.  Click the **Download JSON** button (looks like a downward arrow over a line).
3.  **Rename** the downloaded file to `client_secrets.json`.
4.  **Move** this file into your backend folder:
    ```
    d:\clipcut\backend\client_secrets.json
    ```

## Step 6: Authenticate
1.  Open your terminal in `d:\clipcut`.
2.  Run the setup script:
    ```powershell
    python setup_youtube_auth.py
    ```
3.  A browser window will open. detailed Log in with your YouTube account and allow the permissions.
4.  Once done, you will see `Authentication complete`.

**You are now ready to auto-upload!**

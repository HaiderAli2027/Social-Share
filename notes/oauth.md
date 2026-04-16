# OAuth 2.0: From Basic to Advanced

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Concepts](#basic-concepts)
3. [How OAuth Works](#how-oauth-works)
4. [OAuth Flows](#oauth-flows)
5. [Implementation with Django-Allauth](#implementation-with-django-allauth)
6. [Advanced Topics](#advanced-topics)
7. [Security Best Practices](#security-best-practices)

---

## Introduction

**What is OAuth?**

OAuth (Open Authorization) is an open standard for **secure delegation of access**. It allows users to grant third-party applications permission to access their resources (like LinkedIn profile, emails, etc.) **without sharing their passwords**.

**Traditional Problem (Pre-OAuth):**

```
User → LinkedIn Password → Your App
              ↓
         Your App has user's password
         Massive security risk!
```

**OAuth Solution:**

```
User → "Login with LinkedIn" Button → LinkedIn's Authorization Server
                                           ↓
                                    User approves
                                           ↓
                                    LinkedIn gives Token to Your App
                                           ↓
                                    Your App uses Token (NOT password)
```

---

## Basic Concepts

### **1. OAuth Actors**

| Actor                    | Role                                                     |
| ------------------------ | -------------------------------------------------------- |
| **Resource Owner**       | The user (you) who has data on LinkedIn                  |
| **Resource Server**      | LinkedIn's servers that store your data                  |
| **Authorization Server** | LinkedIn's server that verifies identity & issues tokens |
| **Client Application**   | Your app (Social Share)                                  |

### **2. Core Terminology**

| Term                   | Meaning                                    | Example                             |
| ---------------------- | ------------------------------------------ | ----------------------------------- |
| **Client ID**          | Your app's identifier                      | `abc123xyz789`                      |
| **Client Secret**      | Your app's password (keep secret!)         | `super_secret_key_12345`            |
| **Authorization Code** | Temporary code that proves user approved   | `code_xyz_123_temp`                 |
| **Access Token**       | Credential to access user's data           | `linkedin_token_xyz_abc_123`        |
| **Refresh Token**      | Token to get new Access Token when expired | `refresh_xyz_123`                   |
| **Redirect URI**       | URL user returns to after authorization    | `http://localhost:8000/callback`    |
| **Scope**              | Permissions requested                      | `r_basicprofile`, `w_member_social` |

### **3. Token vs Password**

```
PASSWORD:
- User shares with app
- App can do anything with account
- If app is hacked, hacker has password
- No way to revoke except change password

ACCESS TOKEN:
- Limited permissions (only what user approved)
- Can expire automatically (time-limited)
- Can be revoked without changing password
- Hacker only gets that specific token's access
```

---

## How OAuth Works

### **Simplified Flow (4 Steps)**

```
Step 1: User clicks "Login with LinkedIn"
        ↓
Step 2: Your app redirects to LinkedIn
        LinkedIn shows: "This app wants: name, email, profile"
        User clicks: "Approve"
        ↓
Step 3: LinkedIn redirects back to your app
        Includes: authorization_code
        ↓
Step 4: Your app (backend) exchanges code for Access Token
        Now your app can access user's LinkedIn data
```

### **Detailed Sequence**

```
┌─────────────┐                    ┌──────────────┐
│   Your      │                    │   LinkedIn   │
│   Django    │                    │   Servers    │
│   App       │                    │              │
└─────────────┘                    └──────────────┘
     │                                    │
     │ 1. User clicks "LinkedIn Login"    │
     │    Redirects to:                   │
     │    linkedin.com/oauth/authorize    │
     │────────────────────────────────────→
     │                                    │
     │                      2. Shows consent screen
     │                         User clicks "Allow"
     │                                    │
     │ 3. Redirects back with code       │
     │    to: yoursite.com/callback      │
     │←────────────────────────────────────
     │    ?code=AUTHORIZATION_CODE
     │
     │ 4. Backend exchanges code
     │    POST to linkedin.com/oauth/token
     │    client_id=XXX
     │    client_secret=YYY
     │    code=AUTHORIZATION_CODE
     │────────────────────────────────────→
     │                                    │
     │                      5. Returns Access Token
     │                         {
     │                           "access_token": "token_xyz",
     │                           "expires_in": 3600
     │                         }
     │←────────────────────────────────────
     │
     │ 6. Use token to fetch user data
     │    GET /v2/me
     │    Authorization: Bearer token_xyz
     │────────────────────────────────────→
     │                                    │
     │                      7. Returns user profile
     │                         {
     │                           "id": "123",
     │                           "name": "John Doe"
     │                         }
     │←────────────────────────────────────
```

---

## OAuth Flows

### **1. Authorization Code Flow** (Most Common)

**Used for**: Web apps, mobile apps, desktop apps

**Best for**: Server-side applications with backend

```
User → "Login with LinkedIn"
     ↓
Redirects to LinkedIn authorization URL
     ↓
User approves
     ↓
LinkedIn returns authorization_code
     ↓
Your backend exchanges code for access_token (SECRET COMMUNICATION)
     ↓
Your app saves access_token in database
     ↓
Use token to access user's LinkedIn data
```

**Why the 2-step exchange?**

- Authorization code is short-lived & tied to redirect URI
- Backend exchanges it securely (client_secret stays on server)
- Access token is what actually accesses data

### **2. Implicit Flow** (Deprecated - Don't Use)

```
Direct exchange of credentials in browser
⚠️ Dangerous: Access token exposed in browser
```

### **3. Client Credentials Flow**

**Used for**: Server-to-server communication (not user-focused)

```
Your App → LinkedIn API
         client_id: XXX
         client_secret: YYY
         ↓
         Returns Access Token
         (No user involved)
```

### **4. Refresh Token Flow**

**Problem**: Access tokens expire (usually 1-3 hours)

**Solution**: Use refresh token to get new access token

```
Access Token expires
     ↓
Your App uses Refresh Token
     ↓
LinkedIn returns new Access Token
     ↓
Continue using new token
```

---

## Implementation with Django-Allauth

### **What is django-allauth?**

Library that **abstracts OAuth complexity**. It handles:

- Redirect flows
- Token exchange
- Token storage
- User creation
- Profile sync

### **How Your App Uses It**

```python
# models.py
from django.conf import settings
User = settings.AUTH_USER_MODEL

# When user logs in with LinkedIn:
# 1. Django-allauth handles OAuth flow
# 2. Creates SocialAccount record linking user to LinkedIn
# 3. Stores access_token in database

from allauth.socialaccount.models import SocialAccount

# Your code can then:
linkedin_account = user.socialaccount_set.get(provider='linkedin')
access_token = linkedin_account.socialtoken_set.first().token

# Use token to make API calls:
import requests
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("https://api.linkedin.com/v2/me", headers=headers)
```

### **Setup Flow in Django-Allauth**

**Step 1: User Visits**

```
yoursite.com/accounts/linkedin/login/
```

**Step 2: Redirected to LinkedIn OAuth**

```
django-allauth handles this automatically
```

**Step 3: User Approves**

```
LinkedIn redirects back to callback URL
```

**Step 4: Django-Allauth Processes**

```python
# Behind scenes:
# 1. Extracts authorization_code from URL
# 2. Exchanges for access_token (securely on backend)
# 3. Fetches user profile from LinkedIn
# 4. Creates/updates User and SocialAccount
# 5. Logs user in
# 6. Stores access_token in SocialToken model
```

### **Database Structure**

```
User Table
├── id
├── username
├── email
└── ...

SocialAccount Table (links user to LinkedIn)
├── user_id (FK to User)
├── provider: "linkedin"
├── uid: "linkedin_user_id_12345"
└── extra_data: {...}

SocialToken Table (stores credentials)
├── account_id (FK to SocialAccount)
├── token: "access_token_xyz_abc"
├── token_secret: (for OAuth 1.0, unused for LinkedIn)
└── expires_in: 3600
```

---

## Advanced Topics

### **1. Token Expiration & Refresh**

```python
# LinkedIn tokens expire in 3600 seconds (1 hour)
social_token = user.socialaccount_set.get(
    provider='linkedin'
).socialtoken_set.first()

# Check if expired:
from datetime import timedelta
from django.utils import timezone

if social_token.expires_at < timezone.now():
    # Token expired, use refresh_token to get new one
    # (django-allauth may handle this automatically)
    pass
```

### **2. Scope Permissions**

**What are scopes?**
Permissions you're requesting from user

**LinkedIn Scopes:**

```
r_basicprofile     # Read basic profile (deprecated, use openid profile)
r_emailaddress     # Read email
w_member_social    # Write to LinkedIn feed (post updates)
r_member_social    # Read member social data
```

**How to request**:

```python
# settings.py
SOCIALACCOUNT_PROVIDERS = {
    'linkedin_oauth2': {
        'SCOPE': [
            'profile',
            'email',
            'w_member_social',  # For posting
        ]
    }
}
```

### **3. Error Handling**

```python
import requests

def post_to_linkedin(user, content):
    try:
        social_account = user.socialaccount_set.get(provider='linkedin')
        token = social_account.socialtoken_set.first().token

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json={"content": content},
            timeout=10
        )

        if response.status_code == 401:
            # Unauthorized - token likely expired or revoked
            raise Exception("LinkedIn authentication failed")
        elif response.status_code == 403:
            # Forbidden - insufficient permissions
            raise Exception("App lacks permission to post")
        elif response.status_code >= 500:
            # Server error - retry later
            raise Exception("LinkedIn server error")

        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        raise Exception("LinkedIn API timeout")
    except Exception as e:
        raise Exception(f"Failed to post: {str(e)}")
```

### **4. Revoking Access**

```python
# User disconnects LinkedIn from your app
def disconnect_linkedin(user):
    try:
        social_account = user.socialaccount_set.get(provider='linkedin')
        social_account.delete()
        # LinkedIn doesn't require explicit revocation in most cases
    except:
        pass
```

### **5. Multiple Accounts (User has multiple LinkedIn profiles)**

```python
# Get all LinkedIn accounts for user
linkedin_accounts = user.socialaccount_set.filter(provider='linkedin')

# Usually only one, but theoretically possible to have multiple
for account in linkedin_accounts:
    token = account.socialtoken_set.first().token
    # Use each token
```

---

## Security Best Practices

### **1. Never Expose Client Secret**

```python
# ❌ BAD - Never put in frontend code
client_secret = "my_super_secret"  # Visible to users!

# ✅ GOOD - Keep in environment variables
import os
client_secret = os.getenv('LINKEDIN_SECRET')
```

### **2. Validate Redirect URI**

```
OAuth requires exact redirect URI match
If you register: http://localhost:8000/callback
Then LinkedIn only allows: http://localhost:8000/callback
Not: http://localhost:8000/callback/ (extra slash fails!)
```

### **3. Support HTTPS Only in Production**

```python
# Django-allauth checks for HTTPS in production
# Set in settings:
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### **4. Protect Access Tokens**

```python
# ❌ Bad: Sending token in URL
redirect("https://api.com/data?token=xyz")

# ✅ Good: Sending token in Authorization header
headers = {"Authorization": f"Bearer {token}"}
requests.get("https://api.com/data", headers=headers)
```

### **5. Handle Token Revocation**

```
Scenario: User changes password on LinkedIn
→ All tokens automatically invalidated
→ Your app gets 401 error
→ Clear stored tokens
→ Force user to re-authenticate
```

### **6. Audit Logging**

```python
def log_oauth_event(user, event_type, provider, status):
    # Log when:
    # - User authenticates
    # - Token expires
    # - API calls made
    # - Errors occur

    from django.contrib.admin.models import LogEntry
    # Use Django's logging framework
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"{user} {event_type} with {provider}: {status}")
```

---

## Quick Reference

### **OAuth with LinkedIn in Your App**

```python
# User logs in → django-allauth handles flow → SocialAccount created

# To use:
from allauth.socialaccount.models import SocialAccount

social_account = user.socialaccount_set.get(provider='linkedin')
access_token = social_account.socialtoken_set.first().token

# Make API calls:
import requests
headers = {"Authorization": f"Bearer {access_token}"}
requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, ...)
```

### **Common Errors**

| Error                | Cause                        | Fix                                      |
| -------------------- | ---------------------------- | ---------------------------------------- |
| 401 Unauthorized     | Token expired or invalid     | Get new token via refresh flow           |
| 403 Forbidden        | App lacks scope permission   | User must re-authorize with new scopes   |
| Invalid redirect_uri | Doesn't match registered URL | Check exact URL in LinkedIn app settings |
| Invalid client_id    | Wrong ID or not registered   | Verify app is created on LinkedIn        |

---

## Summary

**OAuth is**: Secure, passwordless authentication using tokens

**Flow**:

1. User approves → 2. Get authorization code → 3. Exchange for token → 4. Use token to access data

**In your app**: Django-allauth handles all complexity, you just use the token

**Security**: Never expose secrets, always use HTTPS, validate tokens

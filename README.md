# Social Share Scheduler

## Project Overview

**Name**: Social Share Scheduler

**Purpose**: A sophisticated Django application that allows users to:

- Schedule social media posts to multiple platforms
- Compose posts with rich content
- Publish at optimal times
- Track publishing status
- Extend to multiple platforms seamlessly

**Tech Stack**:

- **Backend**: Django
- **Authentication**: Django-Allauth with OAuth
- **Job Scheduler**: Inngest (serverless workflows)
- **Database**: SQLite

**Status**: MVP (Minimum Viable Product) completed for LinkedIn

---


### **Project Structure**

```
Social Share/
├── src/
│   ├── manage.py
│   ├── db.sqlite3
│   ├── SocialSharing/           # Django Project Config
│   │   ├── settings.py
│   │   ├── urls.py              # Main URL router
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── Posts/                   # App for managing posts
│   │   ├── models.py            # Post model
│   │   ├── views.py
│   │   ├── admin.py
│   │   └── migrations/
│   ├── Scheduler/               # Inngest functions
│   │   ├── functions.py         # Workflow logic
│   │   ├── views.py             # Webhook handler
│   │   ├── client.py            # Inngest client config
│   │   └── urls.py (implied)
│   └── helper/                  # Utility functions
│       └── linkedin.py          # LinkedIn API client
├── notebooks/                   # Jupyter notebooks for testing
│   ├── 01-hello-world.ipynb
│   ├── 02-allauth-linkedin-user-token.ipynb
│   └── 04-linkedin-helper-function.ipynb
├── notes/                       # Documentation (you are here)
│   ├── oauth.md
│   ├── inngest.md
│   └── scheduler.md
├── requirements.txt             # Dependencies
├── rav.yaml                     # Rav task configuration
└── docker-compose.yml           # Inngest dev server
```

### **Components**

| Component         | Purpose               | Technology     |
| ----------------- | --------------------- | -------------- |
| **Posts App**     | Data model for posts  | Django ORM     |
| **Scheduler App** | Workflow automation   | Inngest        |
| **Helper Module** | Platform integrations | Custom Python  |
| **OAuth**         | User authentication   | Django-Allauth |
| **Inngest**       | Job scheduling        | Serverless     |

---

## How It Works

### **Flow Diagram**

```
┌──────────────────────────────────┐
│  User Creates Post               │
│  - Sets content                  │
│  - Selects platforms             │
│  - Chooses publish time          │
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Django Post Model               │
│  - Saves to database             │
│  - Triggers save() method        │
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Publish Event to Inngest        │
│  - Event: "posts/post.scheduled" │
│  - Data: {object_id: 123}        │
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Inngest Workflow Trigge red      │
│  - post_scheduler function starts│
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Step 1: Record Start Time       │
│  - Save workflow_start_at        │
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Step 2: Wait Until Publish Time │
│  - Sleep until scheduled time    │
│  - Non-blocking (frees resources)│
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Step 3: Share to LinkedIn       │
│  - Call LinkedIn API             │
│  - Post content                  │
│  - Handle errors with retry      │
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Step 4: Record Completion       │
│  - Save workflow_complete_at     │
│  - Mark as shared               │
└──────────────────────────────────┘
              ↓
┌──────────────────────────────────┐
│  Monitor in Dashboard            │
│  - View status in Inngest UI     │
│  - Check logs for debugging      │
└──────────────────────────────────┘
```

### **Timeline Example**

```
2026-04-16 14:00:00
└─ User creates post with share_at=16:30:00

2026-04-16 14:02:00
└─ Post.save() triggers
   └─ Publishes "posts/post.scheduled" event
   └─ Inngest receives event

2026-04-16 14:02:05
└─ Inngest calls post_scheduler()
   ├─ Step: record workflow start
   ├─ Step: sleep_until(16:30:45)
   └─ (function paused, worker freed)

2026-04-16 16:30:45
└─ Scheduled time reached
   └─ Inngest resumes post_scheduler()
   └─ Step: post to LinkedIn API
   └─ LinkedIn receives request
   └─ Content published

2026-04-16 16:30:50
└─ Step: record workflow completion
└─ Function returns success
└─ Inngest dashboard shows ✅ Completed
```

---

## Database Schema

### **Post Model**

```python
class Post(models.Model):
    # Relationships
    user = ForeignKey(User)  # Author of post

    # Content
    content = TextField()     # Post text

    # Scheduling
    share_now = BooleanField(default=None, null=True)
    share_at = DateTimeField(null=True)  # When to publish

    # Platforms
    share_on_linkedin = BooleanField(default=False)

    # Workflow Tracking
    share_start_at = DateTimeField(null=True)
    share_complete_at = DateTimeField(null=True)
    shared_at_linkedin = DateTimeField(null=True)

    # Metadata
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    # Methods
    def clean(self)              # Validate before save
    def save(self)               # Publish event on save
    def perform_share_on_linkedin() # Execute sharing
    def verify_can_share_on_linkedin() # Pre-checks
```

### **Related Models (Django-Allauth)**

```
User (Django built-in)
└─ SocialAccount (allauth)
   └─ For LinkedIn connection
   └─ Stores: uid, provider, extra_data
   └─ SocialToken
      └─ Stores: access_token, expires_at
```

### **Inngest State** (External)

```
Inngest Dashboard tracks:
- Function execution ID
- Attempt number (if retry)
- Step results (cached)
- Start/end times
- Logs
- Output
```

---

## OAuth Integration

### **Flow in Your App**

```
1. User clicks "Login with LinkedIn"
   └─ Redirected to /accounts/linkedin/login/

2. Django-Allauth handles OAuth
   ├─ Redirects to LinkedIn authorization
   ├─ User approves
   └─ Exchanged for access_token

3. SocialAccount created
   └─ Links user to LinkedIn profile
   └─ Stores access_token

4. When sharing post
   ├─ Retrieve access_token from SocialToken
   ├─ Use Bearer token in API calls
   └─ LinkedIn accepts authenticated requests
```

### **Getting LinkedIn Token**

```python
# In helper/linkedin.py
social_account = user.socialaccount_set.get(provider='linkedin')
access_token = social_account.socialtoken_set.first().token

# Use in API calls
headers = {"Authorization": f"Bearer {access_token}"}
requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers)
```

### **Security Considerations**

✅ **Implemented**:

- Access token stored in database (Django-Allauth handles)
- Never exposes token in URLs
- Uses Bearer authentication (HTTP headers)

⚠️ **Future Improvements**:

- Implement token refresh on expiration
- Add audit logging for API access
- Implement rate limiting

---

## Inngest Workflow

### **post_scheduler Function**

**Triggered by**: Event `posts/post.scheduled`

**Steps**:

1. `"fetch-current-timestamp"` - Record workflow start
2. `"wait-until-publish-time"` - Sleep until scheduled time
3. `"share-to-linkedin"` - Execute LinkedIn sharing
4. `"record-workflow-end"` - Record workflow completion

**Error Handling**:

- Validates post exists
- Checks LinkedIn connection
- Retries up to 3 times
- Logs errors for debugging

**Idempotency**:

- Checks if already shared (`shared_at_linkedin` field)
- Won't duplicate posts if retry happens

### **Configuration**

```python
@inngest_client.create_function(
    fn_id="post_scheduler",
    trigger=inngest.TriggerEvent(event="posts/post.scheduled"),
    retries=3  # Retry failed attempts
)
def post_scheduler(ctx: inngest.Context) -> str:
    # See notes/inngest.md for detailed explanation
```

---

## API Endpoints

### **Current Endpoints**

| Method         | Path                        | Purpose                       |
| -------------- | --------------------------- | ----------------------------- |
| `GET/POST/PUT` | `/api/inngest`              | Webhook for Inngest callbacks |
| `GET/POST`     | `/accounts/login/`          | User authentication           |
| `GET/POST`     | `/accounts/linkedin/login/` | LinkedIn OAuth                |
| `GET`          | `/admin/`                   | Django admin panel            |

### **Django Admin**

Accessible at `/admin/`:

- Create/edit posts
- View user accounts
- Manage SocialAccounts
- View logs

---

## Future Roadmap

### **Phase 1: Enhance LinkedIn** (Weeks 1-2)

**Goals**:

- ✅ Single post scheduling (COMPLETED)
- Add image/video support to posts
- Implement batch posting
- Add scheduling template system

**Tasks**:

```
- [ ] Add media field to Post model
- [ ] Extend linkedin.py to handle media
- [ ] Create UI for image upload
- [ ] Test with different media types
```

### **Phase 2: Multi-Platform Support** (Weeks 3-4)

**Goals**:

- Support Instagram posting
- Support Twitter/X posting
- Create platform-agnostic sharing system

**Architecture**:

```
Post Model
├─ share_on_linkedin: Boolean
├─ share_on_instagram: Boolean
└─ share_on_twitter: Boolean

When post.save():
├─ If linkedin → Publish event "posts/post.scheduled"
├─ If instagram → Publish event "posts/instagram.scheduled"
└─ If twitter → Publish event "posts/twitter.scheduled"

Inngest Functions:
├─ post_scheduler (LinkedIn)
├─ post_scheduler_instagram (Instagram)
└─ post_scheduler_twitter (Twitter)
```

**Tasks**:

```
- [ ] Create Instagram OAuth app
- [ ] Implement instagram.py helper
- [ ] Add instagram_scheduler function
- [ ] Create Twitter OAuth app
- [ ] Implement twitter.py helper
- [ ] Add twitter_scheduler function
```

### **Phase 3: News Aggregator** (Weeks 5-6)

**Project**: Auto-publish daily news to a dedicated LinkedIn page

**Architecture**:

```
News API (e.g., NewsAPI)
│
├─ Daily Cron Job: "news_aggregator_job"
│  └─ Runs every day at 08:00 AM
│  └─ Fetches top 5 news items
│  └─ Formats as posts
│
├─ For each news item:
│  ├─ Create Post instance
│  ├─ Schedule for specific times
│  │  └─ 08:30 AM - First post
│  │  └─ 12:00 PM - Repost
│  │  └─ 18:00 PM - Evening post
│  └─ Publish event to Inngest
│
└─ Inngest Workflow:
   └─ Share to dedicated company LinkedIn page
   └─ Track engagement
   └─ Store metrics
```

**Benefits**:

- Automatic content generation
- Consistent posting schedule
- Build authority in industry
- Drive traffic to website

**Tasks**:

```
- [ ] Set up NewsAPI account
- [ ] Create news_aggregator.py
- [ ] Implement daily scheduler cron
- [ ] Create news formatting logic
- [ ] Set up company LinkedIn page
- [ ] Create company page OAuth
- [ ] Test end-to-end workflow
```

### **Phase 4: Advanced Features** (Weeks 7-8)

**Goals**:

- Analytics dashboard
- Post performance tracking
- A/B testing support
- Content recommendations

**Features**:

```
- [ ] Track post engagement (likes, comments, shares)
- [ ] Store metrics in database
- [ ] Create analytics dashboard
- [ ] Implement A/B testing (same post different times)
- [ ] AI-powered content suggestions
- [ ] Hashtag recommendations
```

### **Phase 5: Team Collaboration** (Weeks 9-10)

**Goals**:

- Multiple users per company
- Approval workflows
- Scheduling calendar
- Comment management

**Features**:

```
- [ ] Team/Organization model
- [ ] Role-based permissions (Admin, Editor, Viewer)
- [ ] Approval workflow (editor → admin → publish)
- [ ] Calendar view of scheduled posts
- [ ] Comment notifications & responses
```

---

## Development Workflow

### **Running Locally**

```bash
# 1. Activate virtual environment
. venv/Scripts/Activate.ps1

# 2. Start Inngest dev server (Terminal 1)
docker compose up

# 3. Run Django app (Terminal 2)
cd src
python manage.py runserver

# 4. Optional: Start Jupyter for testing (Terminal 3)
rav run notebook
```

### **Creating a Post via Django Shell**

```python
python manage.py shell

from django.contrib.auth import get_user_model
from Posts.models import Post
from django.utils import timezone
from datetime import timedelta

User = get_user_model()
user = User.objects.first()

post = Post.objects.create(
    user=user,
    content="This is my scheduled post!",
    share_on_linkedin=True,
    share_at=timezone.now() + timedelta(minutes=5),
    share_now=False
)
# This triggers the workflow automatically!
```

### **Monitoring Workflow**

1. Open Inngest Dashboard: `http://localhost:8288`
2. View published events
3. Check function executions
4. Monitor step results
5. Debug errors with logs

### **Testing Workflow**

See `/notebooks/04-linkedin-helper-function.ipynb` for testing examples

---

## Troubleshooting

### **Event Not Triggering Function**

**Symptom**: Event published but function doesn't run

**Checklist**:

```
[ ] Function added to INSTALLED_APPS? (Scheduler)
[ ] Event name matches trigger? (posts/post.scheduled)
[ ] Django app running? (python manage.py runserver)
[ ] Inngest dev server running? (docker compose up)
[ ] Function registered in Inngest dashboard?
[ ] Check logs for errors in both Django & Inngest
```

### **LinkedIn Sharing Fails**

**Symptom**: Step "share-to-linkedin" fails repeatedly

**Causes**:

```
1. User not authenticated with LinkedIn
   → Solution: User must log in via OAuth

2. Access token expired
   → Solution: Implement token refresh

3. Insufficient permissions (scope)
   → Solution: Request 'w_member_social' scope

4. LinkedIn API rate limit
   → Solution: Implement backoff & retry

5. Post content violates LinkedIn policy
   → Solution: Validate content before sharing
```

### **Workflow Doesn't Resume After Crash**

**Symptom**: Server crashes, workflow doesn't continue

**Potential Causes**:

```
1. Steps not properly cached
   → Review step_id naming

2. Function not idempotent
   → Check for duplicate actions

3. Inngest connection lost
   → Verify network connectivity
```

### **Database Migrations Failing**

**Symptom**: `makemigrations` detects no changes

**Solution**:

```bash
# 1. Verify Post app in INSTALLED_APPS
grep "Posts" src/SocialSharing/settings.py

# 2. Explicitly specify app
python manage.py makemigrations Posts

# 3. Run migrations
python manage.py migrate
```

---

## Performance Considerations

### **Current Limitations**

- **Single server**: Not horizontally scalable
- **SQLite**: Not suitable for production (use PostgreSQL)
- **Blocking operations**: All LinkedIn API calls are sync

### **Future Optimizations**

```python
# Batch operations
# Instead of 1 post at a time, handle 100 scheduled posts

# Caching
# Cache LinkedIn profile data to reduce API calls

# Async operations
# Use async/await for API calls

# Database indexing
# Index on share_at for faster query

# Rate limiting
# Implement token bucket to respect LinkedIn limits
```

---

## Contributing Guidelines

### **Code Style**

```python
# Use type hints
def send_email(user_id: int) -> dict:
    pass

# Use meaningful variable names
linkedin_access_token = get_token()  # ✅
token = get_token()  # ❌

# Log important events
ctx.logger.info(f"Sharing post {post_id}")

# Handle errors gracefully
try:
    result = risky_operation()
except SpecificError as e:
    ctx.logger.error(f"Expected error: {e}")
except Exception as e:
    ctx.logger.exception(f"Unexpected error: {e}")
    raise
```

### **Adding Features**

1. Create feature branch: `git checkout -b feature/instagram-support`
2. Write tests for new functionality
3. Update documentation (this file)
4. Submit PR for review

---

## Resources

| Resource        | Link                                                                          | Purpose                |
| --------------- | ----------------------------------------------------------------------------- | ---------------------- |
| Django Tutorial | https://docs.djangoproject.com/                                               | Learn Django framework |
| Django-Allauth  | https://django-allauth.readthedocs.io/                                        | OAuth setup            |
| Inngest Docs    | https://www.inngest.com/docs                                                  | Workflows & scheduling |
| LinkedIn API    | https://learn.microsoft.com/en-us/linkedin/shared/api-guide/rest-api-overview | API reference          |
| OAuth 2.0       | See notes/oauth.md                                                            | OAuth explanation      |

---

## Contact & Support

**Project Owner**: [Your Name]
**Last Updated**: 2026-04-17
**Status**: MVP - Active Development

For questions or issues:

1. Check troubleshooting section
2. Review documentation in `/notes`
3. Consult Inngest logs
4. Open issue on project repo

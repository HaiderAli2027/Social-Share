# Inngest: From Basic to Advanced

## Table of Contents

1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Architecture](#architecture)
4. [Functions & Steps](#functions--steps)
5. [State Management](#state-management)
6. [Error Handling & Retries](#error-handling--retries)
7. [Scheduling & Durability](#scheduling--durability)
8. [Best Practices](#best-practices)
9. [Advanced Patterns](#advanced-patterns)

---

## Introduction

**What is Inngest?**

Inngest is a **serverless workflow engine** for running **reliable, long-running background tasks** with automatic retries, scheduling, and observation.

**Problem It Solves:**

```
❌ Traditional Approach:
   Task → if server crashes → LOST
   Task finishes step 2 → if restart → re-execute step 1 (bad!)
   Task takes 2 hours → server freezes

✅ Inngest Approach:
   Task saved to persistent storage
   If crash → resume from checkpoint (not restart)
   Steps run independently (one hangs, others continue)
   Can schedule for future, pause, resume, observe
```

**Real-World Example:**

```
Your app needs to:
1. Process user payment
2. Wait 5 seconds
3. Send confirmation email
4. Schedule follow-up in 24 hours
5. Log completion

Without Inngest:
- Can't wait 5 seconds (server would block)
- Email fails? Manual retry
- Follow-up? Yet another cron job

With Inngest:
- Built-in sleep (doesn't block)
- Automatic retry
- Scheduling included
- All tracked automatically
```

---

## Core Concepts

### **1. What is a Function?**

An Inngest function is a **reliable, resumable workflow** triggered by events.

```python
import inngest

inngest_client = inngest.Inngest(app_id="my_app")

@inngest_client.create_function(
    fn_id="send_email",
    trigger=inngest.TriggerEvent(event="user/signup")
)
def send_signup_email(ctx: inngest.Context) -> str:
    user_id = ctx.event.data["user_id"]
    # ... send email ...
    return "email sent"
```

**Key Properties:**

- **Triggered by events**: `user/signup`, `order/placed`, etc.
- **Runs on backend**: Safe to do operations here
- **Reliable**: Built-in retry, durability
- **Observable**: Can see status in dashboard

### **2. What are Steps?**

Steps are **checkpoints** in your function where:

- Results are cached
- Retries don't re-execute previous steps
- Complex logic is broken down

```python
def my_function(ctx: inngest.Context):
    # Step 1: Run and cache result
    user_data = ctx.step.run("fetch-user", get_user)

    # Step 2: If step 1 succeeds, run this
    email_sent = ctx.step.run("send-email", send_email)

    # Step 3: Even if step 2 fails, step 1 result is cached
    # On retry, step 1 doesn't re-run

    return "done"
```

### **3. Context Object**

The `ctx: inngest.Context` provides:

```python
@inngest_client.create_function(...)
def my_func(ctx: inngest.Context):
    # Event data
    user_id = ctx.event.data["user_id"]

    # Execution metadata
    run_id = ctx.run_id
    attempt = ctx.attempt  # Which retry attempt?
    logger = ctx.logger

    # Step execution
    result = ctx.step.run("step_id", callable)
    ctx.step.sleep_until("name", datetime)

    return result
```

### **4. Events**

Events **trigger** Inngest functions.

```python
# Publishing an event
inngest_client.send_sync(
    inngest.Event(
        name="user/signup",
        id="signup_unique_123",
        data={"user_id": 456, "email": "user@example.com"}
    )
)

# Function listening for it
@inngest_client.create_function(
    trigger=inngest.TriggerEvent(event="user/signup")
)
def on_user_signup(ctx: inngest.Context):
    user_id = ctx.event.data["user_id"]
    # ...
```

---

## Architecture

### **How Inngest Works**

```
┌─────────────────────────────────────────────────────────────┐
│                    Inngest Architecture                      │
└─────────────────────────────────────────────────────────────┘

Your Django App                 Inngest Backend
┌──────────────┐               ┌──────────────────┐
│              │               │                  │
│ Event        │─────publish──→│ Event Queue      │
│ Published    │               │                  │
└──────────────┘               └──────────────────┘
                                       ↓
                                    ┌──────────────────────┐
                                    │ Function Dispatcher  │
                                    │ (matches event)      │
                                    └──────────────────────┘
                                            ↓
                                    ┌──────────────────────┐
Your Django App                     │ Function Execution   │
┌──────────────────┐               │ (calls your function)│
│                  │               └──────────────────────┘
│ Function Handler │←──────call────────────┤
│ (your code)      │                       │
│                  │                       │
└──────────────────┘                ┌──────────────────────┐
                                    │ State Storage        │
                                    │ (caches results)     │
                                    └──────────────────────┘
```

### **Request/Response Flow**

```
1. Event Published
   inngest.send_sync(Event(...))
                ↓
2. Inngest Receives Event
   Stores in queue
                ↓
3. Dispatcher Finds Matching Function
   Looks up: "user/signup" → send_email_function
                ↓
4. Inngest Calls Your Function
   HTTP POST to /api/inngest
   Body: {event: {...}, steps: {...}, attempt: 1}
                ↓
5. Your Django App Executes
   Runs: send_email_function(ctx)
   Caches step results
                ↓
6. Returns Response to Inngest
   {status: "completed", output: "..."}
                ↓
7. Inngest Marks Complete
   Updates dashboard, stores result
```

---

## Functions & Steps

### **Creating Functions**

```python
# Basic function
@inngest_client.create_function(
    fn_id="send_notification",
    trigger=inngest.TriggerEvent(event="notification/scheduled")
)
def send_notification(ctx: inngest.Context) -> str:
    user_id = ctx.event.data["user_id"]
    # ... send notification ...
    return "sent"
```

**Parameters:**

- `fn_id`: Unique identifier for this function
- `trigger`: What event(s) trigger this function
- `retries`: How many times to retry on failure
- `timeout`: Max execution time

### **Running Steps**

**Purpose**: Break work into atomic, retryable chunks

```python
def my_function(ctx: inngest.Context):
    # STEP 1: Fetch data
    user = ctx.step.run(
        "fetch-user",
        lambda: User.objects.get(id=ctx.event.data["user_id"])
    )

    # STEP 2: Process
    result = ctx.step.run(
        "process-data",
        lambda: process_user_data(user)
    )

    # STEP 3: Save
    saved = ctx.step.run(
        "save-result",
        lambda: save_to_database(result)
    )

    return {"status": "complete", "result": saved}
```

**Step Lifecycle:**

```
First Execution:
┌─────────────────┐
│ Step 1: Run     │ ← Executes, caches result
└─────────────────┘
         ↓
┌─────────────────┐
│ Step 2: Run     │ ← If this fails...
└─────────────────┘

On Retry:
┌─────────────────┐
│ Step 1: Skipped │ ← Inngest returns cached result
└─────────────────┘
         ↓
┌─────────────────┐
│ Step 2: Re-run  │ ← Retry only the failed step
└─────────────────┘
```

### **Step Serialization**

**Critical Rule**: Step functions must return **serializable data**

```python
# ❌ BAD - Returns Django model (not serializable)
result = ctx.step.run("fetch", lambda: User.objects.get(id=1))

# ✅ GOOD - Returns dict
result = ctx.step.run(
    "fetch",
    lambda: User.objects.get(id=1).__dict__
)

# ✅ ALSO GOOD - Returns primitives
result = ctx.step.run("compute", lambda: {"sum": 10, "count": 5})
```

### **Sleep/Delay**

```python
# Sleep for duration
ctx.step.sleep("delay", timedelta(seconds=10))

# Sleep until specific time (preferred)
ctx.step.sleep_until(
    "wait-for-email",
    timezone.now() + timedelta(hours=1)
)

# No blocking! Worker is freed to handle other functions
```

**Why `sleep_until` instead of `time.sleep()`?**

```
time.sleep(3600):
- Blocks entire worker for 1 hour
- Worker can't handle other tasks
- Wastes resources

ctx.step.sleep_until():
- Pauses execution
- Worker handles other functions
- At scheduled time, resumes automatically
- Efficient resource usage
```

---

## State Management

### **How Steps Cache State**

```python
def process_order(ctx: inngest.Context):
    order_id = ctx.event.data["order_id"]

    # First execution:
    # 1. Fetches order
    # 2. Inngest stores: {step_id: "fetch-order", output: {...}}
    # 3. Processes
    # 4. Fails on email step

    # On retry:
    # 1. Inngest sees step "fetch-order" already ran
    # 2. Returns cached output directly (no re-fetch)
    # 3. Continues to process
    # 4. Retries email step

    order = ctx.step.run("fetch-order", get_order)

    process_order(order)

    ctx.step.run("send-email", send_confirmation_email)
```

### **Accessing Previously Calculated Values**

```python
def workflow(ctx: inngest.Context):
    # Before: Calculate
    timestamp = ctx.step.run("get-timestamp", get_now)

    # Now: Timestamp stays same even on retry
    print(timestamp)  # Same value!

    # Do more work
    ctx.step.run("send-email", ...)

    # On retry, timestamp doesn't change
    # Function is deterministic
```

---

## Error Handling & Retries

### **Default Retry Behavior**

```python
# By default: 3 retries with exponential backoff
@inngest_client.create_function(
    fn_id="send_email",
    trigger=inngest.TriggerEvent(event="email/send")
)
def send_email(ctx: inngest.Context):
    # First attempt
    # If exception → Wait 1 second → Retry 1
    # If still fails → Wait 2 seconds → Retry 2
    # If still fails → Wait 4 seconds → Retry 3
    # If still fails → Mark as failed
    pass
```

### **Custom Retry Config**

```python
@inngest_client.create_function(
    fn_id="critical_task",
    trigger=inngest.TriggerEvent(event="task/start"),
    retries=5  # Retry 5 times instead of 3
)
def critical_task(ctx: inngest.Context):
    pass
```

### **Error Logging**

```python
def process_payment(ctx: inngest.Context):
    try:
        # Make payment
        payment_result = ctx.step.run(
            "charge-card",
            lambda: stripe.charge(...)
        )
    except stripe.error.CardError as e:
        # Log error for investigation
        ctx.logger.error(f"Card declined: {e}")
        # Usually don't want to retry card errors
        raise IngestError(f"Payment failed: {e}")
    except stripe.error.RateLimitError as e:
        # Retry rate limit errors
        ctx.logger.warning(f"Rate limited, will retry: {e}")
        raise  # Let Inngest retry
    except Exception as e:
        ctx.logger.exception(f"Unexpected error: {e}")
        raise


class IngestError(Exception):
    """Don't retry this error"""
    pass
```

### **Manual Retries (Deprecated Pattern)**

```python
# ❌ Don't do this - inngest handles retries
import time

def process(ctx: inngest.Context):
    for attempt in range(3):
        try:
            return do_work()
        except Exception:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise

# ✅ Instead - let inngest handle it
def process(ctx: inngest.Context):
    return do_work()
    # Inngest automatically retries if exception raised
```

---

## Scheduling & Durability

### **Delayed Execution**

```python
# Publish event for future execution
inngest_client.send_sync(
    inngest.Event(
        name="reminder/send",
        data={"user_id": 123},
        ts=(
            timezone.now() + timedelta(days=1)
        ).timestamp() * 1000  # milliseconds
    )
)

# Inngest queues this and executes tomorrow
```

### **Durability Guarantee**

```
Event published
     ↓
Persisted to storage (not lost if server crashes)
     ↓
Function called
     ↓
Steps cached (not lost if crash mid-execution)
     ↓
If server dies:
     → On restart: Resumes from last completed step
     → Doesn't re-execute previous steps
     → Continues from where it left off
```

### **Example Durable Workflow**

```python
def send_daily_digest(ctx: inngest.Context):
    user_id = ctx.event.data["user_id"]

    # Step 1: Fetch articles (5 seconds)
    articles = ctx.step.run("fetch-articles", fetch_articles)
    # ✓ Saved to storage

    # Step 2: Format email (2 seconds)
    email_html = ctx.step.run("format-email", format_email)
    # ✓ Saved to storage

    # Server crashes here! ❌

    # On restart:
    # - Inngest skips steps 1 & 2 (returns cached)
    # - Continues to step 3

    # Step 3: Send email (3 seconds)
    ctx.step.run("send-email", send_email)

    return "digest sent"
```

---

## Best Practices

### **1. Use Meaningful Step IDs**

```python
# ❌ Vague
ctx.step.run("step1", do_something)
ctx.step.run("step2", do_something_else)

# ✅ Clear
ctx.step.run("fetch-user-from-database", get_user)
ctx.step.run("validate-email-format", validate_email)
```

### **2. Make Functions Idempotent**

**Idempotent**: Running multiple times produces same result

```python
# ❌ Not idempotent - creates multiple charges if retried
def charge_user(ctx: inngest.Context):
    stripe.charge(user_id, amount)

# ✅ Idempotent - checks if already charged
def charge_user(ctx: inngest.Context):
    user = get_user()
    if user.already_charged:
        return "already charged"
    stripe.charge(user_id, amount)
```

### **3. Query Instead of Reference Objects**

```python
# ❌ Bad - object reference not serializable across retries
user_obj = User.objects.get(id=1)
ctx.step.run("send-email", lambda: send_email(user_obj))

# ✅ Good - query by ID in step
def send_email_for_user(user_id):
    user = User.objects.get(id=user_id)
    return send_email(user)

ctx.step.run("send-email", lambda: send_email_for_user(user_id))
```

### **4. Validate Input at Start**

```python
def process_order(ctx: inngest.Context):
    # Validate immediately
    order_id = ctx.event.data.get("order_id")
    if not order_id:
        ctx.logger.error("Missing order_id")
        return {"status": "failed", "reason": "invalid_input"}

    # Proceed with work
    order = ctx.step.run("fetch-order", get_order)
```

### **5. Return Structured Data**

```python
# ❌ Vague result
return "success"

# ✅ Structured result
return {
    "status": "success",
    "order_id": 123,
    "amount_charged": 99.99,
    "timestamp": timezone.now().isoformat()
}
```

### **6. Use Logging, Not Print**

```python
# ❌ Print might not show in logs
print("Processing order")

# ✅ Inngest logger shows in dashboard
ctx.logger.info("Processing order")
ctx.logger.error("Failed to charge: {error}")
```

### **7. Handle Long Operations**

```python
# ❌ Don't block waiting
import time
time.sleep(300)  # 5 minutes!

# ✅ Inngest scheduler
ctx.step.sleep_until(
    "wait-for-processing",
    timezone.now() + timedelta(minutes=5)
)
```

---

## Advanced Patterns

### **1. Parallel Steps**

```python
def process_multiple(ctx: inngest.Context):
    user_ids = [1, 2, 3, 4, 5]

    # Run all in parallel (limited concurrency)
    email_results = []
    for user_id in user_ids:
        result = ctx.step.run(
            f"send-email-to-{user_id}",
            lambda uid=user_id: send_email(uid)
        )
        email_results.append(result)

    return {"sent": len(email_results)}
```

### **2. Conditional Logic**

```python
def order_workflow(ctx: inngest.Context):
    order = ctx.step.run("fetch-order", get_order)

    if order.amount > 1000:
        # Require approval
        approval = ctx.step.run(
            "request-approval",
            request_manual_approval
        )
        if not approval:
            return {"status": "rejected"}

    # Process payment
    ctx.step.run("charge-card", charge_card)

    return {"status": "success"}
```

### **3. Chaining Functions (Fan-out)**

```python
# Function 1: Receives event
@inngest_client.create_function(
    fn_id="order_placed",
    trigger=inngest.TriggerEvent(event="order/placed")
)
def on_order_placed(ctx: inngest.Context):
    order_id = ctx.event.data["order_id"]

    # Trigger other functions
    inngest_client.send_sync(
        inngest.Event(
            name="order/processing_started",
            data={"order_id": order_id}
        )
    )
    inngest_client.send_sync(
        inngest.Event(
            name="notification/send_confirmation",
            data={"order_id": order_id}
        )
    )

# Function 2: Processes order
@inngest_client.create_function(
    fn_id="process_order",
    trigger=inngest.TriggerEvent(event="order/processing_started")
)
def process_order(ctx: inngest.Context):
    # ...

# Function 3: Sends notification
@inngest_client.create_function(
    fn_id="send_confirmation",
    trigger=inngest.TriggerEvent(event="notification/send_confirmation")
)
def send_confirmation(ctx: inngest.Context):
    # ...
```

### **4. Error Handling with Different Strategies**

```python
def send_critical_notification(ctx: inngest.Context):
    try:
        # Try email
        ctx.step.run("send-email", send_email)
    except EmailFailedError:
        ctx.logger.warning("Email failed, trying SMS")
        try:
            # Fallback to SMS
            ctx.step.run("send-sms", send_sms)
        except SMSFailedError:
            ctx.logger.error("Both email and SMS failed")
            # Still need to track it somehow
            ctx.step.run("log-failure", log_notification_failure)
            raise

    return {"status": "notified"}
```

### **5. Monitoring & Observability**

```python
def monitored_task(ctx: inngest.Context):
    ctx.logger.info(f"Starting (attempt {ctx.attempt})")

    try:
        result = ctx.step.run("main-work", do_work)
        ctx.logger.info(f"Success: {result}")
        return result
    except Exception as e:
        ctx.logger.exception(f"Failed with error: {e}")

        # Could send alert
        inngest_client.send_sync(
            inngest.Event(
                name="alert/task_failed",
                data={
                    "function_id": ctx.function_id,
                    "error": str(e),
                    "attempt": ctx.attempt
                }
            )
        )
        raise
```

---

## Summary Table

| Feature                      | How                               | When                |
| ---------------------------- | --------------------------------- | ------------------- |
| **Reliable Execution**       | Built-in retries                  | Always              |
| **Resumable Workflows**      | Step caching                      | After crashes       |
| **Delayed Execution**        | `ts` parameter                    | Schedule for future |
| **Breaking Work into Steps** | `ctx.step.run()`                  | Complex operations  |
| **Waiting (Non-blocking)**   | `ctx.step.sleep_until()`          | Scheduled tasks     |
| **Idempotency**              | Design functions to be repeatable | Every function      |
| **Error Handling**           | Try/catch + logging               | Handle edge cases   |
| **Observability**            | Dashboard + logging               | Monitor production  |

---

## Common Patterns in Your Project

### **Your Post Scheduler (Current)**

```python
@inngest_client.create_function(
    fn_id="post_scheduler",
    trigger=inngest.TriggerEvent(event="posts/post.scheduled")
)
def post_scheduler(ctx: inngest.Context) -> str:
    # 1. Record start time (step 1)
    # 2. Sleep until publish time (non-blocking)
    # 3. Publish to LinkedIn (step 2)
    # 4. Record end time (step 3)
    # 5. Return success

    # Each is a checkpoint - if anything fails, resumable
```

### **For Instagram Integration (Future)**

```python
@inngest_client.create_function(
    fn_id="post_to_instagram",
    trigger=inngest.TriggerEvent(event="posts/published_linkedin")
)
def share_to_instagram(ctx: inngest.Context):
    # Run after LinkedIn share completes
    post_id = ctx.event.data["post_id"]

    # Mirror post to Instagram
    ctx.step.run("share-instagram", share_instagram)
```

# Project Features Log

This file tracks the features implemented in the Real-Time Task Manager to avoid duplicate work.

## Implemented Features

### 1. User and Role Models
- Added `Role` model with values: `admin`, `manager`, `employee`.
- Added custom `User` model inheriting from Django's `AbstractUser`, with a foreign key to `Role`.
- Set `AUTH_USER_MODEL = 'Users.User'` in `settings.py`.
- Included `Users` app in `INSTALLED_APPS` in `settings.py`.
- Populated database with the fixed `Role` values.

### 2. User CRUD API Endpoints & Role Management
- Configured Django REST Framework and added it to `INSTALLED_APPS`.
- Created custom permission class `IsAdminOrManagerUserAccess` to restrict User endpoints:
  - Admins have full access.
  - Managers have POST (create) and GET (list/retrieve) access.
- Developed `UserSerializer` using `SlugRelatedField(slug_field='name')` for roles, enabling human-readable string values (`"employee"`) instead of integer IDs in the API.
- Developed `UserViewSet.create()` function logic (`POST /api/users/`):
  - Intercepts requests to explicitly block managers from assigning any role other than `'employee'`.
  - Executes `self.perform_create(serializer)` to safely save the new user to the database.
  - Immediately utilizes `AccessToken.for_user(new_user)` to generate a specialized 10-minute JWT token with a custom `temp=True` claim for the newly created user.
  - Returns this `temp_token` directly in the HTTP 201 JSON response, which the manager can securely distribute to the employee for first-time setup.

### 3. Task Management
- Added `Task` model containing fields like title, description, priority, status, and dates.
- Configured a `FileField` on `Task` for attachments (`attachment`) with `MEDIA_URL` and `MEDIA_ROOT` settings.
- Defined relationships linking tasks to an owner (`created_by`) and multiple assignees (`assigned_to`).
- Implemented `TaskViewSet` with strict role-based access control (`IsManagerOrAssignedEmployeeTaskPermission`):
  - **Managers:** Full CRUD access. Can assign tasks only to 'employee' roles. `perform_create()` automatically sets the `created_by` field to `request.user`.
  - **Employees:** Read-only access to their assigned tasks. Overridden `update()` and `partial_update()` allow employees to update only the `status` field.
  - **Admins:** Explicitly blocked from managing tasks.
  - Overridden `get_queryset()` to hide completed tasks from the default list view for all users. Managers can view them by appending `?status=completed` to the URL.

### 4. Real-Time WebSockets & Notifications System
- Integrated Django Channels and Daphne ASGI server using `InMemoryChannelLayer` for broadcasting events.
- Created `NotificationConsumer` at `ws/notifications/` to handle authenticated user connections.
- Added `Notification` model to store system alerts persistently.
- Real-time events broadcast via `async_to_sync(channel_layer.group_send)`:
  - **Task Assignment:** When an employee is assigned a task, an event is triggered (via `TaskViewSet.perform_create`).
  - **Task Update:** When an employee marks a task as completed (via `TaskViewSet.perform_update`), a notification is generated directed at the manager who originally created the task.

### 5. JWT Authentication & Security API
- Replaced standard Django session authentication with JWT using `rest_framework_simplejwt`.
- Developed `LoginView` (APIView) at `POST /login/`:
  - Validates credentials using `authenticate()`.
  - Upon success, calls `RefreshToken.for_user(user)` to generate custom tokens.
  - Returns standard `access` and `refresh` tokens alongside a serialized `userDetail` payload using `UserSerializer(user).data`.
- Developed `logout_view` (APIView) at `POST /logout/`:
  - Extracts the `refresh` token from the payload.
  - Utilizes `rest_framework_simplejwt.token_blacklist` to securely invalidate refresh tokens server-side via `token.blacklist()`.
- Registered `/api/token/refresh/` via `TokenRefreshCustomView` for fetching new access tokens.

### 6. Temporary Password & Force Password Change Flow
- Rather than forcing temporary passwords into the database, we handle them ephemerally via secure tokens.
- **The Flow:**
  - The Manager receives the `temp_token` upon creating the employee and shares it with them.
  - The Employee directly hits the custom `ForceChangePasswordView` (`POST /api/auth/force-change-password/`) with the `temp_token` and their desired `new_password`.
- **ForceChangePasswordView Logic:**
  - Extracts the token and validates it strictly using `AccessToken(temp_token_str)`.
  - Enforces the `token.get('temp')` claim check to prevent users from bypassing the system using normal access tokens.
  - Updates the user's password using `user.set_password()` and commits the change directly (`update_fields=['password']`).
- Developed `ChangePasswordView` (`POST /api/auth/change-password/`) for standard authenticated users to update passwords by verifying their `old_pass` via `user.check_password()`.

### 7. Background Tasks & Scheduling (Celery)
- Initialized Celery in `celery.py` and `__init__.py`, configuring Redis (`redis://127.0.0.1:6379/0`) as the broker and result backend.
- Installed `django_celery_beat` for cron scheduling.
- Implemented asynchronous tasks in `Users/tasks.py`:
  - **`send_assignment_email`:** Triggered asynchronously via Django Signals (`m2m_changed` in `Users/signals.py`). When an employee is added to `Task.assigned_to` (`action == "post_add"`), the signal queues `.delay(instance.id, user_id)` to instantly send an assignment email using Django's `send_mail` without blocking the API response thread.
  - **`send_daily_reminders`:** A Celery Beat scheduled task configured in `settings.py` (`CELERY_BEAT_SCHEDULE`) to run every day at **9:00 AM UTC** (`crontab(hour=9, minute=0)`). It queries the DB for `User.objects.filter(assigned_tasks__status__in=[Status.PENDING, Status.IN_PROGRESS])` and sends a compiled email summary of all overdue/pending tasks.

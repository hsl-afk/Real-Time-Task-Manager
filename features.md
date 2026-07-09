# Project Features Log

This file tracks the features implemented in the Real-Time Task Manager to avoid duplicate work.

## Implemented Features

### 1. User and Role Models
- Added `Role` model with values: `admin`, `manager`, `employee`.
- Added custom `User` model inheriting from Django's `AbstractUser`, with a foreign key to `Role`.
- Set `AUTH_USER_MODEL = 'Users.User'` in `settings.py`.
- Included `Users` app in `INSTALLED_APPS` in `settings.py`.
- Populated database with the fixed `Role` values.

### 2. User CRUD API Endpoints
- Configured Django REST Framework and added it to `INSTALLED_APPS`.
- Created `IsAdminRole` custom permission class to restrict access only to users with the 'admin' role.
- Created `UserSerializer` that properly handles password hashing on user creation and updates.
- Created `UserViewSet` containing standard CRUD operations, protected by authentication and the `IsAdminRole` permission.
- Registered endpoints at `/api/users/`.

### 3. Premium Login UI
- Configured Django's built-in `LoginView` to serve at the root URL `/`.
- Set up redirect logic to `/api/users/` upon successful authentication in `settings.py`.
- Developed a high-end, responsive login page featuring glassmorphism, fluid animations, and a modern dark-mode aesthetic.

### 4. Task Management
- Added `Task` model containing fields like title, description, priority, status, and dates.
- Defined relationships linking tasks to an owner (`created_by`) and multiple assignees (`assigned_to`).
- Applied successful database migrations for the new `Task` schema without affecting older models.
- Implemented `TaskViewSet` with strict role-based access control:
  - **Managers:** Full CRUD access. Can assign tasks only to 'employee' roles. `created_by` is auto-filled.
  - **Employees:** Read-only access to their assigned tasks, with permission to update only the `status` field.
  - **Admins:** Explicitly blocked from managing tasks.
  - Form validation exclusively restricts the `assigned_to` field dropdown to `employee` users.
  - Completed tasks are hidden from the default list view for all users. Managers can view them by appending `?status=completed` to the URL.
  - Managers can optionally attach a single file to a task during creation or update (e.g. PDFs, images). Employees can view/download these attachments via the provided URL.

### 5. Notification System
- Added `Notification` model to store system alerts (recipient, message, timestamp).
- When an employee updates a task status to `COMPLETED`, the API automatically generates a notification directed at the manager who originally created the task.
- Created `/api/notifications/` endpoint so managers can read their own alerts.

### 6. Real-Time Updates (WebSockets)
- Integrated Django Channels and Daphne ASGI server.
- Uses `InMemoryChannelLayer` for broadcasting events.
- Created `NotificationConsumer` at `ws/notifications/` to handle authenticated user connections.
- Automatically pushes JSON messages in real-time over WebSockets when:
  - An employee is assigned a new task.
  - A manager updates a task.
  - An employee marks a task as completed.

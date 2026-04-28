# Graph Report - /Users/harshalpimpalshende/VSCode and IDE/NYU/DuesAndDos/Git/team6-mon-spring26  (2026-04-27)

## Corpus Check
- Corpus is ~35,539 words - fits in a single context window. You may not need a graph.

## Summary
- 944 nodes · 1899 edges · 83 communities detected
- Extraction: 53% EXTRACTED · 47% INFERRED · 0% AMBIGUOUS · INFERRED: 894 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_User Accounts & Profile Signals|User Accounts & Profile Signals]]
- [[_COMMUNITY_Custom User Model & Admin|Custom User Model & Admin]]
- [[_COMMUNITY_Expenses Settlement & Chat Tests|Expenses Settlement & Chat Tests]]
- [[_COMMUNITY_Chore Management & Notifications|Chore Management & Notifications]]
- [[_COMMUNITY_Google Calendar Integration|Google Calendar Integration]]
- [[_COMMUNITY_Real-time Chat Messaging|Real-time Chat Messaging]]
- [[_COMMUNITY_Chat Utilities & References|Chat Utilities & References]]
- [[_COMMUNITY_Platform Features & Tech Stack|Platform Features & Tech Stack]]
- [[_COMMUNITY_Expense Tracking & Insights|Expense Tracking & Insights]]
- [[_COMMUNITY_Chore Testing Suite|Chore Testing Suite]]
- [[_COMMUNITY_File Upload & Media Storage|File Upload & Media Storage]]
- [[_COMMUNITY_Expense Pro Tests|Expense Pro Tests]]
- [[_COMMUNITY_OAuth Adapters & Auth Flow|OAuth Adapters & Auth Flow]]
- [[_COMMUNITY_Django App Configuration|Django App Configuration]]
- [[_COMMUNITY_URL Routing Tests|URL Routing Tests]]
- [[_COMMUNITY_S3 Media Storage|S3 Media Storage]]
- [[_COMMUNITY_Database Migrations (Core)|Database Migrations (Core)]]
- [[_COMMUNITY_Chat Init & URLs|Chat Init & URLs]]
- [[_COMMUNITY_Gmail Photo Sync Tests|Gmail Photo Sync Tests]]
- [[_COMMUNITY_Activity Log Tests|Activity Log Tests]]
- [[_COMMUNITY_Chat Group Migration|Chat Group Migration]]
- [[_COMMUNITY_Elastic Beanstalk Config Tests|Elastic Beanstalk Config Tests]]
- [[_COMMUNITY_Django Management Entry|Django Management Entry]]
- [[_COMMUNITY_Code Quality Toolchain|Code Quality Toolchain]]
- [[_COMMUNITY_Expenses App Init|Expenses App Init]]
- [[_COMMUNITY_Chore GCal Migration|Chore GCal Migration]]
- [[_COMMUNITY_Chore Event ID Migration|Chore Event ID Migration]]
- [[_COMMUNITY_ChoreSkip Migration|ChoreSkip Migration]]
- [[_COMMUNITY_Chore Completion Migration|Chore Completion Migration]]
- [[_COMMUNITY_Message Reference Migration|Message Reference Migration]]
- [[_COMMUNITY_Message Deletion Migration|Message Deletion Migration]]
- [[_COMMUNITY_Chat Index Migration|Chat Index Migration]]
- [[_COMMUNITY_Chat Reference Migration|Chat Reference Migration]]
- [[_COMMUNITY_Chores App Init|Chores App Init]]
- [[_COMMUNITY_Expense Amount Migration|Expense Amount Migration]]
- [[_COMMUNITY_Expense Date Migration|Expense Date Migration]]
- [[_COMMUNITY_Settlement Migration|Settlement Migration]]
- [[_COMMUNITY_Activities App Init|Activities App Init]]
- [[_COMMUNITY_Expense Split Type Migration|Expense Split Type Migration]]
- [[_COMMUNITY_Profile Calendar Migration|Profile Calendar Migration]]
- [[_COMMUNITY_Expense Split Amount Migration|Expense Split Amount Migration]]
- [[_COMMUNITY_Expense Settlement Migration|Expense Settlement Migration]]
- [[_COMMUNITY_Avatar Upload Migration|Avatar Upload Migration]]
- [[_COMMUNITY_Expense Settled At Migration|Expense Settled At Migration]]
- [[_COMMUNITY_Expense Split Removal Migration|Expense Split Removal Migration]]
- [[_COMMUNITY_Split Models Migration|Split Models Migration]]
- [[_COMMUNITY_Household & Profile Migration|Household & Profile Migration]]
- [[_COMMUNITY_Google Avatar Migration|Google Avatar Migration]]
- [[_COMMUNITY_Personal Todo Migration|Personal Todo Migration]]
- [[_COMMUNITY_Household Description Migration|Household Description Migration]]
- [[_COMMUNITY_Expense App Migration|Expense App Migration]]
- [[_COMMUNITY_Invite Code Migration|Invite Code Migration]]
- [[_COMMUNITY_User Deactivation Migration|User Deactivation Migration]]
- [[_COMMUNITY_Profile Creation Migration|Profile Creation Migration]]
- [[_COMMUNITY_Expense Split Migration|Expense Split Migration]]
- [[_COMMUNITY_Chat App Init|Chat App Init]]
- [[_COMMUNITY_Fridge Note Migration|Fridge Note Migration]]
- [[_COMMUNITY_Households App Init|Households App Init]]
- [[_COMMUNITY_Activity Log Action Migration|Activity Log Action Migration]]
- [[_COMMUNITY_ASGI Config|ASGI Config]]
- [[_COMMUNITY_Django Settings|Django Settings]]
- [[_COMMUNITY_Home URL Router|Home URL Router]]
- [[_COMMUNITY_WSGI Config|WSGI Config]]
- [[_COMMUNITY_Models Stub|Models Stub]]
- [[_COMMUNITY_Accounts Init|Accounts Init]]
- [[_COMMUNITY_Admin Stub|Admin Stub]]
- [[_COMMUNITY_Activities Init|Activities Init]]
- [[_COMMUNITY_Chat Init|Chat Init]]
- [[_COMMUNITY_Chores Init|Chores Init]]
- [[_COMMUNITY_Expenses Init|Expenses Init]]
- [[_COMMUNITY_Admin Stub (Chat)|Admin Stub (Chat)]]
- [[_COMMUNITY_Households Init|Households Init]]
- [[_COMMUNITY_Migration Init|Migration Init]]
- [[_COMMUNITY_Migration Init (2)|Migration Init (2)]]
- [[_COMMUNITY_Migration Init (3)|Migration Init (3)]]
- [[_COMMUNITY_Admin Stub (Expenses)|Admin Stub (Expenses)]]
- [[_COMMUNITY_Migration Init (4)|Migration Init (4)]]
- [[_COMMUNITY_Migration Init (5)|Migration Init (5)]]
- [[_COMMUNITY_Admin Stub (Households)|Admin Stub (Households)]]
- [[_COMMUNITY_Migration Init (6)|Migration Init (6)]]
- [[_COMMUNITY_Migration Init (7)|Migration Init (7)]]
- [[_COMMUNITY_Migration Init (8)|Migration Init (8)]]
- [[_COMMUNITY_Python Dependencies|Python Dependencies]]

## God Nodes (most connected - your core abstractions)
1. `CustomUser` - 58 edges
2. `Chore` - 57 edges
3. `Profile` - 57 edges
4. `ExpenseViewTests` - 49 edges
5. `AuthAndProfileTests` - 49 edges
6. `GoogleCalendarService` - 46 edges
7. `Household` - 42 edges
8. `ChoreViewTests` - 40 edges
9. `HouseholdSettingsViewTests` - 40 edges
10. `ChatViewTests` - 37 edges

## Surprising Connections (you probably didn't know these)
- `static/ Directory (CSS, JS, images)` --references--> `Dues & Do's Logo - Two semicircles (navy and light blue)`  [INFERRED]
  DEVELOPMENT.md → duesanddos/static/images/logo.png
- `Logo Design: Two offset semicircles - navy (left) and light blue (right), suggesting duality (dues/dos, balance, sharing)` --conceptually_related_to--> `Household Management Platform`  [INFERRED]
  duesanddos/static/images/logo.png → README.md
- `Dues & Do's - Household Management Platform (README)` --references--> `Dues & Do's Logo - Two semicircles (navy and light blue)`  [EXTRACTED]
  README.md → duesanddos/static/images/logo.png
- `django-allauth==65.15.0` --implements--> `Google OAuth2 Authentication`  [INFERRED]
  duesanddos/requirements.txt → README.md
- `google-auth==2.49.1` --implements--> `Google OAuth2 Authentication`  [INFERRED]
  duesanddos/requirements.txt → README.md

## Hyperedges (group relationships)
- **Google OAuth2 Integration Stack** — dep_google_auth, dep_google_auth_oauthlib, dep_google_api_client, dep_django_allauth, concept_google_oauth2 [INFERRED 0.85]
- **AWS S3 Storage Stack** — dep_boto3, dep_django_storages, dep_pillow, concept_amazon_s3 [INFERRED 0.85]
- **Code Quality Toolchain** — dep_black, dep_flake8, dep_pre_commit, dep_coverage, dep_coveralls [INFERRED 0.80]
- **PostgreSQL Database Stack** — dep_psycopg, tech_postgresql, rationale_postgresql_required [EXTRACTED 0.90]
- **Planned Roadmap Features** — concept_expenses_ledger, concept_chore_assignments, concept_household_chat, concept_activity_feed [EXTRACTED 1.00]

## Communities

### Community 0 - "User Accounts & Profile Signals"
Cohesion: 0.03
Nodes (30): Delete the old avatar from S3 whenever a new one is uploaded., fetch_gmail_photo(), When a new user signs up via Google OAuth, fetch their Gmail profile picture, ActivityLogViewTests, test_sync_gcal_overdues_command_deactivated_user(), ChatPollingTests, ActivitiesViewsTests, AuthAndProfileTests (+22 more)

### Community 1 - "Custom User Model & Admin"
Cohesion: 0.04
Nodes (45): AbstractUser, CustomUserAdmin, ProfileAdmin, CustomPasswordChangeForm, Meta, ProfileUpdateForm, RegisterForm, UserUpdateForm (+37 more)

### Community 2 - "Expenses Settlement & Chat Tests"
Cohesion: 0.03
Nodes (4): Settlement, ChatMessageDeletionTests, ExpenseViewTests, HouseholdSettingsViewTests

### Community 3 - "Chore Management & Notifications"
Cohesion: 0.05
Nodes (31): ChoreAdmin, ChoresConfig, activity_notifications(), Provides recent activities and task reminders for the user., ChoreForm, ActivityLog, Chore, log_chore_completion() (+23 more)

### Community 4 - "Google Calendar Integration"
Cohesion: 0.06
Nodes (47): BaseCommand, GoogleCalendarService, Build the Google Calendar event body dict for a chore., Create or update the Google Calendar event for a chore., Manages Google Calendar API interactions with automatic token refresh., Mark a specific occurrence as completed in Google Calendar.         - For ONE_TI, Mark a specific occurrence as overdue in Google Calendar., ChoreCompletion (+39 more)

### Community 5 - "Real-time Chat Messaging"
Cohesion: 0.06
Nodes (14): ConversationAdmin, ConversationParticipantAdmin, MessageAdmin, Conversation, ConversationManager, ConversationParticipant, ConversationQuerySet, ConversationType (+6 more)

### Community 6 - "Chat Utilities & References"
Cohesion: 0.09
Nodes (34): chat_unread_counts(), _build_reference_snapshot(), compute_message_preview_text(), create_message_with_references(), delete_message_for_everyone(), ensure_chat_context(), _format_date(), get_accessible_conversations() (+26 more)

### Community 7 - "Platform Features & Tech Stack"
Cohesion: 0.06
Nodes (40): Activity Feed (Roadmap Feature), Amazon S3 Storage (profile pictures/avatars), Chore Assignments (Roadmap Feature), Expenses Ledger (Roadmap Feature), Glassmorphism UI Design, Google OAuth2 Authentication, Household Chat - Real-time messaging (Roadmap Feature), Household Management Platform (+32 more)

### Community 8 - "Expense Tracking & Insights"
Cohesion: 0.1
Nodes (11): Expense, Meta, InsightsHelpersTests, InsightsViewTests, test_household_descriptor_exception_is_handled(), test_invalid_dates_fall_back_to_default_month_window(), _add_months(), _day_label() (+3 more)

### Community 9 - "Chore Testing Suite"
Cohesion: 0.11
Nodes (1): ChoreViewTests

### Community 10 - "File Upload & Media Storage"
Cohesion: 0.1
Nodes (8): make_upload_path(), Required by Django to serialize this callable in migration files., Convenience alias: make_upload_path('expenses') == UploadToPath('expenses')., Upload-to callable that Django migrations can serialize via deconstruct()., UploadToPath, CustomUserModelTests, ProfileModelTests, UploadToPathTests

### Community 11 - "Expense Pro Tests"
Cohesion: 0.11
Nodes (1): ExpenseProCoverageTests

### Community 12 - "OAuth Adapters & Auth Flow"
Cohesion: 0.18
Nodes (8): CustomAccountAdapter, CustomSocialAccountAdapter, Redirect back to profile after an existing user connects a Google account, Always return False so new social users are redirected to the signup form., Standard login redirect, DefaultAccountAdapter, DefaultSocialAccountAdapter, AdapterTests

### Community 13 - "Django App Configuration"
Cohesion: 0.14
Nodes (7): AppConfig, AccountsConfig, ActivitiesConfig, ChatConfig, ExpensesConfig, HouseholdsConfig, InsightsConfig

### Community 14 - "URL Routing Tests"
Cohesion: 0.25
Nodes (1): URLTests

### Community 15 - "S3 Media Storage"
Cohesion: 0.29
Nodes (6): MediaStorage, Store user-uploaded media under the 'media/' prefix in S3., S3Boto3Storage, CustomStoragesTests, Test that MediaStorage has the correct properties.         Mocking __init__ to a, test_media_storage_properties()

### Community 16 - "Database Migrations (Core)"
Cohesion: 0.29
Nodes (1): Migration

### Community 17 - "Chat Init & URLs"
Cohesion: 0.29
Nodes (1): Tests for chat message deletion behavior.

### Community 18 - "Gmail Photo Sync Tests"
Cohesion: 0.29
Nodes (1): test_fetch_gmail_photo_existing_avatar()

### Community 19 - "Activity Log Tests"
Cohesion: 0.33
Nodes (1): ActivityLogModelTests

### Community 20 - "Chat Group Migration"
Cohesion: 0.5
Nodes (1): Migration

### Community 21 - "Elastic Beanstalk Config Tests"
Cohesion: 0.5
Nodes (2): SimpleTestCase, ElasticBeanstalkConfigTests

### Community 22 - "Django Management Entry"
Cohesion: 0.67
Nodes (2): main(), Run administrative tasks.

### Community 23 - "Code Quality Toolchain"
Cohesion: 1.0
Nodes (3): black==25.11.0 (Code formatter), flake8==7.3.0 (Linter), pre-commit>=4.5.1 (Git hook framework)

### Community 24 - "Expenses App Init"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Chore GCal Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 26 - "Chore Event ID Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 27 - "ChoreSkip Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 28 - "Chore Completion Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 29 - "Message Reference Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 30 - "Message Deletion Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 31 - "Chat Index Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 32 - "Chat Reference Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 33 - "Chores App Init"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Expense Amount Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 35 - "Expense Date Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 36 - "Settlement Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 37 - "Activities App Init"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Expense Split Type Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 39 - "Profile Calendar Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 40 - "Expense Split Amount Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 41 - "Expense Settlement Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 42 - "Avatar Upload Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 43 - "Expense Settled At Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 44 - "Expense Split Removal Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 45 - "Split Models Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 46 - "Household & Profile Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 47 - "Google Avatar Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 48 - "Personal Todo Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 49 - "Household Description Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 50 - "Expense App Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 51 - "Invite Code Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 52 - "User Deactivation Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 53 - "Profile Creation Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 54 - "Expense Split Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 55 - "Chat App Init"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Fridge Note Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 57 - "Households App Init"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Activity Log Action Migration"
Cohesion: 1.0
Nodes (1): Migration

### Community 59 - "ASGI Config"
Cohesion: 1.0
Nodes (1): ASGI config for duesanddos project.  It exposes the ASGI callable as a module-le

### Community 60 - "Django Settings"
Cohesion: 1.0
Nodes (1): Django settings for duesanddos project. Generated by "django-admin startproject"

### Community 61 - "Home URL Router"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "WSGI Config"
Cohesion: 1.0
Nodes (1): WSGI config for duesanddos project.  It exposes the WSGI callable as a module-le

### Community 63 - "Models Stub"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Accounts Init"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Admin Stub"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Activities Init"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Chat Init"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Chores Init"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Expenses Init"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Admin Stub (Chat)"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Households Init"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Migration Init"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Migration Init (2)"
Cohesion: 1.0
Nodes (0): 

### Community 74 - "Migration Init (3)"
Cohesion: 1.0
Nodes (0): 

### Community 75 - "Admin Stub (Expenses)"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "Migration Init (4)"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Migration Init (5)"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Admin Stub (Households)"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Migration Init (6)"
Cohesion: 1.0
Nodes (0): 

### Community 80 - "Migration Init (7)"
Cohesion: 1.0
Nodes (0): 

### Community 81 - "Migration Init (8)"
Cohesion: 1.0
Nodes (0): 

### Community 82 - "Python Dependencies"
Cohesion: 1.0
Nodes (1): Python Dependencies (requirements.txt)

## Knowledge Gaps
- **73 isolated node(s):** `Run administrative tasks.`, `google_sync_data: list of (user_id, google_event_id)`, `Migration`, `Migration`, `Migration` (+68 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Expenses App Init`** (2 nodes): `__init__.py`, `urls.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chore GCal Migration`** (2 nodes): `Migration`, `0005_remove_chore_google_event_id_choregoogleevent.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chore Event ID Migration`** (2 nodes): `Migration`, `0004_chore_google_event_id.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ChoreSkip Migration`** (2 nodes): `Migration`, `0003_choreskip.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chore Completion Migration`** (2 nodes): `Migration`, `0002_alter_chore_start_date_chorecompletion.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Message Reference Migration`** (2 nodes): `Migration`, `0004_messagereference_snapshots.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Message Deletion Migration`** (2 nodes): `Migration`, `0005_message_deletion_fields.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chat Index Migration`** (2 nodes): `Migration`, `0006_rename_chat_hiddem_user_id_7c4521_idx_chat_hidden_user_id_6eceed_idx.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chat Reference Migration`** (2 nodes): `Migration`, `0003_messagereference_and_more.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chores App Init`** (2 nodes): `__init__.py`, `urls.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Amount Migration`** (2 nodes): `Migration`, `0004_alter_expense_amount_alter_expensesplit_amount_owed_and_more.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Date Migration`** (2 nodes): `Migration`, `0003_alter_expense_date_spent.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Settlement Migration`** (2 nodes): `Migration`, `0002_alter_expense_options_settlement.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Activities App Init`** (2 nodes): `__init__.py`, `urls.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Split Type Migration`** (2 nodes): `Migration`, `0010_alter_expense_split_type.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Profile Calendar Migration`** (2 nodes): `Migration`, `0016_profile_default_calendar_view_profile_theme.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Split Amount Migration`** (2 nodes): `Migration`, `0012_expensesplit_amount_owed.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Settlement Migration`** (2 nodes): `Migration`, `0013_remove_expensesplit_is_settled_and_more.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Avatar Upload Migration`** (2 nodes): `Migration`, `0006_avatar_unique_upload_path.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Settled At Migration`** (2 nodes): `Migration`, `0014_expensesplit_is_settled_expensesplit_settled_at_and_more.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Split Removal Migration`** (2 nodes): `Migration`, `0011_remove_expensesplit_amount_owed_and_more.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Split Models Migration`** (2 nodes): `Migration`, `0015_split_models_to_new_apps.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Household & Profile Migration`** (2 nodes): `Migration`, `0004_household_remove_profile_google_avatar_url_and_more.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Google Avatar Migration`** (2 nodes): `Migration`, `0003_profile_google_avatar_url.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Personal Todo Migration`** (2 nodes): `Migration`, `0017_profile_personal_todo.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Household Description Migration`** (2 nodes): `Migration`, `0007_household_default_rules_household_description.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense App Migration`** (2 nodes): `Migration`, `0008_expense.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Invite Code Migration`** (2 nodes): `Migration`, `0005_alter_household_invite_code.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `User Deactivation Migration`** (2 nodes): `Migration`, `0018_customuser_is_deactivated.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Profile Creation Migration`** (2 nodes): `Migration`, `0002_profile.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expense Split Migration`** (2 nodes): `Migration`, `0009_expense_split_type_expensesplit.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chat App Init`** (2 nodes): `__init__.py`, `urls.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Fridge Note Migration`** (2 nodes): `Migration`, `0002_household_fridge_note.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Households App Init`** (2 nodes): `__init__.py`, `urls.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Activity Log Action Migration`** (2 nodes): `Migration`, `0002_alter_activitylog_action.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ASGI Config`** (2 nodes): `ASGI config for duesanddos project.  It exposes the ASGI callable as a module-le`, `asgi.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Django Settings`** (2 nodes): `Django settings for duesanddos project. Generated by "django-admin startproject"`, `settings.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Home URL Router`** (2 nodes): `home_redirect()`, `urls.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `WSGI Config`** (2 nodes): `wsgi.py`, `WSGI config for duesanddos project.  It exposes the WSGI callable as a module-le`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Models Stub`** (1 nodes): `models.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Accounts Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Stub`** (1 nodes): `admin.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Activities Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chat Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chores Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Expenses Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Stub (Chat)`** (1 nodes): `admin.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Households Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init (2)`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init (3)`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Stub (Expenses)`** (1 nodes): `admin.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init (4)`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init (5)`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Stub (Households)`** (1 nodes): `admin.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init (6)`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init (7)`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Init (8)`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Python Dependencies`** (1 nodes): `Python Dependencies (requirements.txt)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Custom User Model & Admin` to `User Accounts & Profile Signals`, `Expenses Settlement & Chat Tests`, `Chore Management & Notifications`, `Google Calendar Integration`, `Real-time Chat Messaging`, `Chat Utilities & References`, `Expense Tracking & Insights`, `Chore Testing Suite`, `File Upload & Media Storage`, `Expense Pro Tests`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `CustomUser` connect `Custom User Model & Admin` to `User Accounts & Profile Signals`, `Expenses Settlement & Chat Tests`, `Chore Management & Notifications`, `Google Calendar Integration`, `Real-time Chat Messaging`, `Chat Utilities & References`, `Expense Tracking & Insights`, `Chore Testing Suite`, `File Upload & Media Storage`, `URL Routing Tests`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `ExpenseViewTests` connect `Expenses Settlement & Chat Tests` to `Expense Tracking & Insights`, `Custom User Model & Admin`, `Chore Management & Notifications`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `CustomUser` (e.g. with `InsightsHelpersTests` and `InsightsViewTests`) actually correct?**
  _`CustomUser` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `Chore` (e.g. with `InsightsHelpersTests` and `InsightsViewTests`) actually correct?**
  _`Chore` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `Profile` (e.g. with `InsightsHelpersTests` and `InsightsViewTests`) actually correct?**
  _`Profile` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ExpenseViewTests` (e.g. with `CustomUser` and `Profile`) actually correct?**
  _`ExpenseViewTests` has 8 INFERRED edges - model-reasoned connections that need verification._
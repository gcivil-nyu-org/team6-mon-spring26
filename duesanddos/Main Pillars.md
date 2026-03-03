# Dues & Do's: Main Pillars

Welcome to the foundational documentation for **Dues & Do's**. This document outlines the core principles, security measures, and development guidelines that drive this platform.

---

## 🔒 Security: Must-Haves
We prioritize the protection of user data and financial information above all else.
- **Password Hashing:** All user passwords must be hashed using robust algorithms (Django's default PBKDF2 with SHA256) before resting in the database.
- **Environment Variables:** Secrets (API keys, Database credentials, Secret Keys) are strictly stored in `.env` files and never committed to version control.
- **Authentication:** Sessions must be secured using robust mechanisms (e.g., HttpOnly cookies for JWT or Session authentication) to mitigate XSS attacks.

## 🛡️ Frontend Security
- **Cross-Site Scripting (XSS) Prevention:** The React/Next.js frontend inherently escapes variable inputs to prevent script injection.
- **Cross-Site Request Forgery (CSRF):** Django enforces CSRF tokens for all state-changing API requests made from the browser.
- **Secure Data Transmission:** All data transferred between the client and server must use HTTPS (enforced in production).

## 🐛 Features, Bugs, and Critical Breakpoints
- **Feature Development:** All features should have a clear implementation plan before coding begins. Component reuse is highly encouraged.
- **Bug Tracking:** Any bug that prevents a user from logging in or viewing their dashboard is considered a **Critical Breakpoint** and must be patched immediately before feature work continues.
- **Error Handling:** Graceful error states (e.g., "500 Internal Server Error" boundaries) must be shown to the user without exposing stack traces.

## 🏗️ Technical Stack
- **Backend:** Python / Django / Django REST Framework
- **Frontend:** TypeScript / React / Next.js
- **Database:** PostgreSQL
- **Styling:** Tailwind CSS

---
*“Finally, a way to handle the money stuff without making things weird.”*

# Chat Page Redesign Design

## Goal

Upgrade the `chat/` page into a more robust, dynamic, and visually impressive messaging workspace while staying inside the existing Django template, inline JavaScript, and chat-specific stylesheet. The redesign must feel like a premium modern product, preserve the current server-rendered architecture, and avoid modifying non-chat CSS.

## Scope

In scope:

- `duesanddos/chat/templates/chat/chat.html`
- `duesanddos/static/css/chat.css`
- Chat-page-only client-side behavior embedded in the template

Out of scope:

- Shared layouts, shared CSS, base templates, or global design tokens
- Backend API contract changes
- New JavaScript bundles or frontend framework work
- Changes to non-chat pages

## Design Summary

The page will remain a two-pane chat workspace on desktop, with a stronger distinction between navigation and conversation surfaces. The left pane becomes a structured conversation rail with deeper visual hierarchy, richer metadata, and clear actions. The right pane becomes a layered thread experience with a premium header, improved message presentation, and a more capable composer. On smaller screens, the conversation rail becomes dismissible so the active thread remains the primary focus.

The resulting UI should read as a dedicated messaging product rather than a generic card layout.

## Layout Architecture

### Desktop

- Keep a two-column shell.
- Convert the sidebar into a darker anchored rail with:
  - household identity block
  - compact status or summary chips
  - conversation list with stronger active and unread states
  - direct-message starter section
- Convert the thread area into a layered panel with:
  - top header showing conversation type and title
  - status row describing polling or connection freshness
  - main scrollable message canvas
  - visually docked composer at the bottom

### Mobile and Tablet

- Collapse the layout to one primary thread column.
- Add a mobile toggle button in the thread header to open or close the conversation rail.
- Present the sidebar as an overlay or slide-over panel with backdrop treatment.
- Preserve full access to conversation switching and DM creation without relying on desktop-only interactions.

## Conversation Rail

The conversation rail should feel navigational rather than card-based.

### Household Identity

- Present the active household in a stronger hero block at the top.
- Include short supporting copy that frames the page as the household’s live coordination space.

### Summary Chips

- Add lightweight visual chips for information already available in template context, such as:
  - total visible conversations
  - number of other household members available for DM creation
- Do not introduce new backend data just for metrics.

### Conversation Items

- Redesign each conversation row to include:
  - title
  - short preview text
  - lightweight label for group vs direct
  - unread badge
- Use a stronger active state with a premium highlight treatment.
- Improve hover and focus states so the list feels interactive and polished.
- Handle long previews cleanly with line clamping or truncation.

### Start Direct Message

- Keep the existing DM creation behavior.
- Restyle member buttons to feel like secondary actions within the rail, not plain form controls.
- If there are no other members, preserve the empty-state copy with improved visual treatment.

## Thread Header

The thread header should give the active conversation more presence.

- Keep the conversation title and type.
- Add a compact live-status line for polling state and recent update timing.
- Add a mobile rail-toggle control that is hidden on larger screens.
- Add small conversation context affordances, such as a badge for group or direct chat.

## Message Presentation

Messages should feel closer to a modern messaging client while staying within the current HTML structure.

- Add avatar-style markers generated from usernames or initials in the template and for appended messages in JavaScript.
- Differentiate incoming and outgoing messages more clearly through alignment, background, border, and shadow treatment.
- Improve metadata styling so author and timestamp are readable but secondary.
- Increase message list depth with a softer background, internal padding, and visual rhythm.
- Animate newly appended messages subtly so polling updates feel alive rather than abrupt.

### Scroll Behavior

- On initial load, scroll the thread to the newest messages.
- During polling, auto-scroll only when the user is already near the bottom.
- Preserve the user’s reading position if they have scrolled upward.

## Composer

The composer should feel like a real messaging input instead of a generic form.

- Auto-resize the textarea as the user types, within a reasonable height cap.
- Support `Enter` to send and `Shift+Enter` to insert a newline.
- Keep the existing `POST` submission path.
- Improve the footer with:
  - clearer helper copy
  - send button styling
  - optional character or status text using existing limits and polling info
- Ensure the composer remains usable on narrow screens.

## Live State and Polling Feedback

The page already polls for new messages and unread counts. The redesign should make that behavior visible and better integrated.

- Replace the static “Polling every 5 seconds” copy with a more legible live-status area.
- Update status text when polling succeeds or fails.
- Keep the implementation lightweight and page-local.
- Continue to update the global unread badge and conversation badges exactly as the current script does.

## Accessibility and Robustness

- Preserve semantic structure and labels for the composer.
- Ensure keyboard access for the mobile sidebar toggle and conversation actions.
- Maintain visible focus states across links, buttons, and textarea.
- Use sufficient contrast in both the dark rail and light thread surfaces.
- Avoid relying on hover-only affordances.

## Technical Plan

### Template Changes

- Add structural wrappers and utility elements needed for the richer layout.
- Add data attributes needed by JavaScript for live-status text and sidebar toggling.
- Add avatar or initial placeholders based on existing user data.

### CSS Changes

- Replace the current simple card styling with a page-scoped visual system in `chat.css`.
- Introduce chat-local CSS variables for color, surface, shadow, radius, spacing, and motion.
- Add responsive rules for the mobile overlay sidebar and denser desktop layout.
- Keep selectors scoped to chat-page classes so no other page is affected.

### JavaScript Changes

- Extend the existing inline script instead of introducing a new asset pipeline.
- Add:
  - initial scroll-to-bottom behavior
  - near-bottom detection
  - conditional auto-scroll on new messages
  - textarea auto-resize
  - keyboard submission handling
  - live status text updates
  - mobile sidebar toggle behavior
  - avatar generation for dynamically appended messages
- Preserve the current polling endpoints and `mark_read` behavior.

## Error Handling

- If polling fails, update the live status text without breaking the rest of the page.
- If JavaScript is unavailable, the page should still function as a normal server-rendered chat page with form submission and navigation.
- If there are no messages, preserve the empty state but upgrade the presentation to match the new design.

## Testing Strategy

Primary verification will be:

- Django test suite coverage for existing chat views to ensure no regressions in rendering and posting behavior
- Manual browser verification of:
  - desktop layout
  - mobile sidebar behavior
  - message sending via button and keyboard
  - polling updates and unread badges
  - empty and populated conversation states

No backend behavior changes are planned, so tests should remain focused on rendering integrity and existing chat flows.

## Acceptance Criteria

- The chat page looks materially more premium and product-like than the current implementation.
- The redesign is confined to chat template, chat-local JavaScript, and `chat.css`.
- Desktop and mobile layouts both remain functional.
- Composer behavior is improved through auto-resize and enter-to-send.
- Polling feedback is clearer and incoming messages feel smoother.
- Existing server-rendered navigation and submission flows keep working.

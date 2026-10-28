# Build a React TypeScript Task Manager UI Using My Reference Image

Hello! I would like you to build a small, single-page task management frontend using **React, TypeScript, and Tailwind CSS**.

I will provide a reference image showing the desired UI, along with examples of my existing React code. Please study both carefully before implementing anything.

My priority is to create a clean, visually accurate interface while strictly following my existing coding style, component structure, naming conventions, and implementation patterns.

## 1. Analyze the Reference Image First

Before writing code, carefully examine the provided image and identify:

- The overall page layout and proportions.
- The task listing section and its individual task items.
- The AI chat section, including its conversation area and input field.
- Colors, backgrounds, borders, spacing, typography, and alignment.
- Icons, buttons, badges, and other visible UI elements.
- How the layout should adapt to smaller screens.

Use the reference image as the primary visual guide. Reproduce its layout and styling as closely as reasonably possible rather than inventing a different design.

If any detail is unclear, use sensible design choices consistent with the reference image.

## 2. Technology Stack and Constraints

Use the following technologies:

- **React** for the UI.
- **TypeScript** for components, props, task data, and API responses.
- **Tailwind CSS** for styling.
- React hooks such as `useState` and `useEffect` for local state and lifecycle logic.
- Native `fetch` for API requests unless the existing project already uses another suitable approach.

Please follow these constraints:

- Do not use Redux or any other global state management library.
- Do not introduce unnecessary libraries or dependencies.
- Do not use Framer Motion or any other animation library. Animations are not required for this project.
- Do not overengineer the application.
- Do not introduce a complex architecture for a small, single-page frontend.

Use local component state where appropriate. Keep the application simple, readable, and maintainable.

## 3. Main Page Layout

The page has two primary sections.

### A. Task Listing Section

This section displays tasks fetched from a backend API.

For now, focus on rendering the task list properly. The backend CRUD API will be developed separately, so the frontend should consume an existing API rather than implementing task management logic independently.

Each task should display the relevant information available in the API response:

- Task title.
- Description, when available.
- Status.
- Priority.
- Due date, when available.

Requirements:

- Fetch tasks from the backend API using `useEffect`.
- Store the returned tasks in local state using `useState`.
- Define appropriate TypeScript interfaces or types for the task data.
- Display tasks using a separate, reusable task component.
- Show a loading indicator while fetching data.
- Display a clear error message if the request fails.
- Display a suitable empty state if no tasks are available.
- Use Tailwind CSS to match the reference image.

Keep this section focused on displaying tasks. Do not implement unnecessary task editing, deletion, drag-and-drop, or other CRUD interactions at this stage.

Use a configurable API base URL or an environment variable where appropriate. Do not hardcode the backend URL throughout multiple components.

### B. AI Chat Section

This section represents the AI assistant through which users will eventually manage their tasks.

For now, the chat interface is **UI-only and uses dummy conversation data**. There is no need to connect it to an LLM or implement real chat functionality.

Implement the following visible elements according to the reference image:

- A chat header with an appropriate title or assistant label.
- A conversation area containing a few realistic dummy messages.
- Visually distinct user and assistant messages.
- A message input field.
- A send button.
- Appropriate spacing, alignment, and scrolling behavior.

Use local state for the input field if needed. The send button may remain nonfunctional unless a simple local demonstration is useful.

Do not implement WebSockets, streaming responses, conversation persistence, AI integrations, or backend chat endpoints.

The purpose of this section is to make the page look like a realistic AI-powered task manager while keeping its functionality intentionally limited.

## 4. Component Separation

Please divide the UI into small, meaningful, reusable components.

For example, the structure could look like this:

```text
src/
├── Components/
│   ├── Tasks/
│   │   ├── TaskList.tsx
│   │   └── TaskCard.tsx
│   └── Chat/
│       ├── ChatSection.tsx
│       ├── ChatMessage.tsx
│       └── ChatInput.tsx
├── Pages/
│   └── Home.tsx
├── Services/
│   └── taskService.ts
├── Types/
│   └── task.ts
├── App.tsx
└── main.tsx
```

This is a suggested structure, not a rigid requirement. If my existing project uses a different structure, follow that structure instead.

Keep components focused on their responsibilities:

- `Home`: Composes the main page layout.
- `TaskList`: Fetches or renders the task collection, depending on the chosen component boundaries.
- `TaskCard`: Displays an individual task.
- `ChatSection`: Composes the chat interface.
- `ChatMessage`: Displays an individual message.
- `ChatInput`: Renders the message input and send button.
- `taskService`: Handles API requests related to tasks.
- `task.ts`: Defines the relevant TypeScript types.

Avoid creating a separate component for every minor element. Component separation should improve readability, not add unnecessary complexity.

## 5. Strictly Follow My Coding Style

**This is one of the most important requirements. Please treat my provided code examples as the coding style to follow, not merely as inspiration.**

My existing code follows patterns such as:

- Functional React components using arrow functions.
- Explicit React imports, for example:

  ```tsx
  import React, { useEffect, useState } from 'react'
  ```

- Default exports for components.
- PascalCase component names and filenames, such as `Home.tsx`, `TaskCard.tsx`, and `ChatSection.tsx`.
- camelCase variable names and function names.
- Tailwind CSS utility classes directly in JSX through `className`.
- Simple component composition using JSX.
- Straightforward hooks and event handlers.
- A readable, direct implementation without unnecessary abstractions.

Please preserve these conventions consistently across the new components.

Additional rules:

1. Do not introduce a different coding style just because it is a common industry convention.
2. Do not unnecessarily change naming conventions or folder naming patterns.
3. Do not introduce class components, custom hook abstractions, or design patterns unless there is a clear need.
4. Do not use Redux, Context API, Zustand, or similar global state management tools for this application.
5. Do not introduce CSS modules, styled-components, or a separate styling framework. Use Tailwind CSS.
6. Do not add animations, transitions, or motion effects. Keep the interface static and clean.
7. Avoid unnecessary comments, deeply nested ternary expressions, overly generic components, and excessive abstraction.
8. Keep the code understandable for a developer who is still learning React and TypeScript.

I will provide my code examples below. Please inspect them and follow their conventions as closely as possible while using proper TypeScript typing.

[INSERT MY EXISTING CODE EXAMPLES HERE]

## 6. API Integration

The task API will be implemented separately using FastAPI.

Assume that a task endpoint will be available at a configurable URL, such as:

`GET /api/v1/tasks/`

The exact backend URL and response format may be provided later.

For now:

- Create a small task service responsible for fetching tasks.
- Define a TypeScript `Task` type that matches the expected backend response.
- Handle loading, errors, and empty results.
- Keep API-related logic separate from UI rendering where practical.
- Avoid making assumptions about the response structure if the actual API response is available for inspection.
- Do not build mock task data into the production rendering path just to avoid connecting the API.

If the backend API is not yet available, use a clearly isolated temporary mock response or a configurable API URL so the UI can still be developed and tested. Make it easy to switch to the real endpoint later.

No task mutations are required in this phase.

## 7. Responsive Design and Visual Quality

Use Tailwind CSS to reproduce the reference image as closely as possible.

Pay particular attention to:

- Correct proportions between the task listing and chat sections.
- Consistent padding and spacing.
- Proper alignment of headings, task cards, messages, and controls.
- Appropriate use of borders, rounded corners, and background colors.
- Readable typography and visual hierarchy.
- A consistent color palette.
- Appropriate scrolling behavior for long task lists and chat conversations.
- Responsive behavior on desktop, tablet, and mobile screens.

Do not add decorative elements that are absent from the reference image unless they are needed for usability.

Avoid unnecessary hover animations, entrance effects, and elaborate visual effects.

## 8. Implementation Workflow

Please follow this workflow:

1. Inspect the reference image and identify the main UI sections and their layout.
2. Review my code examples and identify the coding conventions you should preserve.
3. Inspect the existing project structure and configuration before creating or modifying files.
4. Briefly describe the proposed component structure.
5. Implement the page and its components using React, TypeScript, and Tailwind CSS.
6. Integrate the task-list API with loading, error, and empty states.
7. Populate the chat section with realistic dummy messages.
8. Check that all imports, exports, types, and file paths are correct.
9. Verify that the application builds successfully and fix any TypeScript or runtime errors.

Please provide complete code for each new or modified file. If you have access to my project files, work with the existing files instead of recreating the project unnecessarily.

Do not rewrite unrelated files or modify the existing project configuration unless required.

## 9. Scope Restrictions

This phase is limited to the frontend UI and basic task-list fetching.

Please do not implement:

- Backend development or database models.
- AI agent integration.
- Real chat API integration.
- Semantic search.
- Task creation, editing, deletion, or status mutation.
- Redux or another global state manager.
- Animations or motion effects.
- Authentication unless it already exists in the project and is necessary for the API request.

## Expected Outcome

A clean, responsive, single-page React TypeScript application that closely follows my reference image, displays tasks fetched from a FastAPI endpoint, and includes a visually complete AI chat section populated with dummy messages.

The code must be component-separated, use Tailwind CSS, follow my coding style and naming conventions strictly, and remain simple without unnecessary abstractions.

**Please prioritize visual accuracy, consistency with my existing code, and implementation simplicity over adding extra features. Thank you!**
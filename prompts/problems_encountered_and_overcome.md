# AI Provider Switching: Failure and Correction

## Problem Encountered

While building the AI-powered application, switching from one AI
provider to another caused the application to stop working.

## Root Cause

LangChain uses separate integration packages for many AI providers.
Having the core LangChain packages installed does not automatically
provide every provider integration. If an integration package is
missing, importing the provider adapter or initializing its model can
fail.

## How It Was Corrected

I added the provider-specific integration packages to `requirements.txt`
so the dependencies needed by the providers I intend to support are
installed with the project:

``` txt
langchain-openrouter
langchain-openai>=1.0
langchain-anthropic>=1.0
langchain-google-genai>=4.0
langchain-deepseek
```

## Outcome

The dependency configuration now includes the integrations needed for
the intended providers. This makes switching providers more reliable
when each provider is configured with the correct adapter, model
identifier, and API key.

## Lesson Learned

When supporting multiple AI providers:

-   Install the appropriate LangChain integration package for each
    provider.
-   Check package versions for compatibility.
-   Configure the provider name, model identifier, and API key
    correctly.
-   Test each provider independently before relying on provider
    switching.

> **Note:** The package names and version constraints above are recorded
> as supplied for this project. Verify them against the current
> integration documentation and package compatibility before deploying.

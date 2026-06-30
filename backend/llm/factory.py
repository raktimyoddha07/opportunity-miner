from backend.config import settings

def build_llm(config: dict):
    """
    Builds and returns a LangChain chat model based on the provided configuration dictionary.
    Supported providers: ollama, openai, anthropic, groq, gemini, openrouter, custom.
    """
    provider = config.get("provider", "").lower()
    model = config.get("model")
    temperature = config.get("temperature", 0.0)

    if not provider:
        raise ValueError("LLM provider must be specified in config.")
    if not model:
        raise ValueError("LLM model name must be specified in config.")

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        base_url = config.get("base_url") or settings.OLLAMA_BASE_URL
        return ChatOllama(model=model, base_url=base_url, temperature=temperature, format="json")

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = config.get("api_key") or settings.OPENAI_API_KEY
        return ChatOpenAI(model=model, api_key=api_key, temperature=temperature)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = config.get("api_key") or settings.ANTHROPIC_API_KEY
        return ChatAnthropic(model=model, api_key=api_key, temperature=temperature)

    elif provider == "groq":
        from langchain_groq import ChatGroq
        api_key = config.get("api_key") or settings.GROQ_API_KEY
        return ChatGroq(model=model, api_key=api_key, temperature=temperature)

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = config.get("api_key") or settings.GEMINI_API_KEY
        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=temperature)

    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        api_key = config.get("api_key") or settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        base_url = config.get("base_url") or "https://openrouter.ai/api/v1"
        return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=temperature)

    elif provider == "custom":
        from langchain_openai import ChatOpenAI
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        if not base_url:
            raise ValueError("base_url is required for custom LLM provider.")
        return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=temperature)

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

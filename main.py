"""Small startup/configuration check; the chat entrypoint is app.py."""

from core.config import Settings
from core.workflow import Assistant


def main():
    settings = Settings.load()
    assistant = Assistant(settings)
    print(
        f"Validated {len(assistant.menu.items)} menu items. SQLite directory: {settings.data_dir}"
    )
    print(f"Model: OpenRouter / {settings.model}; key configured: {bool(settings.api_key)}")
    print("Run: uv run python -m chainlit run app.py")
    assistant.close()


if __name__ == "__main__":
    main()

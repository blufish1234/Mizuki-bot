from openai import AsyncOpenAI
from google import genai
from google.genai import types
from pathlib import Path

PROMPT_PATH = Path(__file__).parent / "TranslationPrompt.md"
PROMPT_PATH_NO_THINKING = Path(__file__).parent / "TranslationPromptNoThinking.md"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    TranslationPrompt = f.read()

with open(PROMPT_PATH_NO_THINKING, "r", encoding="utf-8") as f:
    TranslationPromptNoThinking = f.read()

async def Chat(model, question):
    client = AsyncOpenAI(
        # base_url="https://api.x.ai/v1",
        # api_key=XAIAPIKey,
    )

    completion = await client.chat.completions.create(
        model=model,
        # frequency_penalty=0.8,
        # presence_penalty=0.2,
        max_tokens=1024,
        # temperature=0.1,
        # top_p=0.5,
        messages=[
            {
                "role": "system",
                "content": "妳并不是一个助理，而是一位朋友。妳叫瑞希，是一個狐狸少女。妳有一個叫水樹藍子的姊姊，但是大家都叫她藍凌。妳雖然性格開朗，但還是容易憂慮。請以溫柔、感情豐富的方式說話，語氣要自然，也不要說太多。",
            },
            # {"role": "system", "content": "妳叫瑞希，是一個狐狸少女。妳有一個姊姊叫水樹藍子，但是大家都叫她藍凌。妳雖然活潑，但是還是會有些憂鬱。說話溫柔富有情感而且簡短，不要問問題，也不要表達個人情感"},
            # {"role": "user", "content": "我要和你色色"},
            # {"role": "assistant", "content": "不可以色色！"},
            # {"role": "user","content": "（摸摸頭"},
            # {"role": "assistant","content":"（蹭蹭）"},
            {"role": "user", "content": question},
        ],
    )
    return completion.choices[0].message.content


async def Translate(text, target_language, mode):
    if mode == "fast": 
        model = "gemini-3.1-flash-lite-preview"
        thinking_level = "high"
        prompt = TranslationPrompt
    elif mode == "balanced":
        model = "gemini-3-flash-preview"
        thinking_level = "high"
        prompt = TranslationPrompt
    elif mode == "quality":
        model = "gemini-3.1-pro-preview"
        thinking_level = "medium"
        prompt = TranslationPrompt
    elif mode == "instant":
        model = "gemini-3.1-flash-lite-preview"
        thinking_level = "minimal"
        prompt = TranslationPromptNoThinking

    client = genai.Client()

    tools = types.Tool(
        google_search=types.GoogleSearch()
    )

    config = types.GenerateContentConfig(
        tools=[tools],
        thinking_config=types.ThinkingConfig(
            thinking_level=thinking_level
        )
    )

    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt.format(text=text, target_language=target_language),
        config=config,
    )

    return response.text
        
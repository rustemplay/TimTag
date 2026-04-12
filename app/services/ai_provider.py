"""
Groq — основной провайдер.
GigaChat — автоматический резервный если Groq недоступен.

В .env нужны оба ключа:
  GROQ_API_KEY=gsk_...
  GIGACHAT_API_KEY=...
  AI_MODEL=llama3-8b-8192   # модель Groq
  GIGACHAT_MODEL=GigaChat   # модель GigaChat
"""
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def chat(prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
    """
    Пробуем Groq. Если упал — автоматически GigaChat.
    Если оба упали — бросаем исключение (ai_client.py поймает и вернёт fallback-текст).
    """
    if settings.groq_api_key:
        try:
            return await _groq(prompt, temperature, json_mode)
        except Exception as e:
            logger.warning(f"Groq недоступен ({e}), переключаемся на GigaChat...")

    if settings.gigachat_api_key:
        return await _gigachat(prompt, temperature)

    raise RuntimeError("Нет доступных AI провайдеров. Проверь GROQ_API_KEY и GIGACHAT_API_KEY в .env")


async def _groq(prompt: str, temperature: float, json_mode: bool) -> str:
    from groq import AsyncGroq
    client = AsyncGroq(api_key=settings.groq_api_key)
    kwargs = dict(
        model=settings.ai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    r = await client.chat.completions.create(**kwargs)
    return r.choices[0].message.content


async def _gigachat(prompt: str, temperature: float) -> str:
    import httpx
    import base64

    creds = base64.b64encode(
        f"{settings.gigachat_api_key}:{settings.gigachat_api_key}".encode()
    ).decode()

    async with httpx.AsyncClient(verify=False, timeout=15) as client:
        # Шаг 1 — получаем токен
        token_r = await client.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Authorization": f"Basic {creds}", "RqUID": "timtag"},
            data={"scope": "GIGACHAT_API_PERS"},
        )
        token_r.raise_for_status()
        token = token_r.json()["access_token"]

        # Шаг 2 — запрос к модели
        r = await client.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": settings.gigachat_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
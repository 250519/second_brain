from openai import OpenAI

from .config import API_KEY, BASE_URL


def get_client() -> OpenAI:
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)

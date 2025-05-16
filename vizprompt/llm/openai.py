'''OpenAI APIと通信するためのモジュール'''
import os
import time
from openai import OpenAI
from .base import BaseGenerator, test

class Settings:
    """
    APIのデフォルト設定を管理するクラス。
    """
    def __init__(self, api_key, url, model):
        self.api_key = api_key
        self.url = url
        self.model = model

class Defaults:
    OpenAI = Settings(
        api_key=os.getenv("OPENAI_API_KEY"),
        url="https://api.openai.com/v1",
        model="gpt-4.1-mini",
    )
    OpenRouter = Settings(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        url="https://openrouter.ai/api/v1",
        model="qwen/qwen3-4b:free",
    )
    Groq = Settings(
        api_key=os.getenv("GROQ_API_KEY"),
        url="https://api.groq.com/openai/v1",
        model="gemma2-9b-it",
    )
    Grok = Settings(
        api_key=os.getenv("GROK_API_KEY"),
        url="https://api.x.ai/v1",
        model="grok-3-mini-latest",
    )

if Defaults.OpenAI.api_key:
    defaults = Defaults.OpenAI
elif Defaults.OpenRouter.api_key:
    defaults = Defaults.OpenRouter
elif Defaults.Groq.api_key:
    defaults = Defaults.Groq
elif Defaults.Grok.api_key:
    defaults = Defaults.Grok
else:
    raise ValueError("環境変数 OPENAI_API_KEY/OPENROUTER_API_KEY/GROQ_API_KEY/GROK_API_KEY が設定されていません。")

class Generator(BaseGenerator):
    def __init__(self, model=None, url=defaults.url, api_key=defaults.api_key):
        """
        OpenAIGeneratorの初期化。

        Args:
            model: 使用するモデルの名前。
            url: APIのURL。
        """
        if model is None:
            model = defaults.model
        super().__init__(model)
        self.url = url
        self.client = OpenAI(base_url=url, api_key=api_key)

    def chat(self, messages):
        """
        OpenAIにプロンプトを送信し、ストリーム応答を取得します。

        Args:
            messages: OpenAIに送信するメッセージのリスト。

        Yields:
            応答のチャンク文字列。
        """
        time1 = time.monotonic()
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )
        time2 = None
        text = ""
        count = 0
        usage = None
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                text += content
                count += 1
                if not time2:
                    time2 = time.monotonic()
                yield content
            if hasattr(chunk, "usage") and chunk.usage:
                usage = chunk.usage.to_dict()
        time3 = time.monotonic()
        self.text = text
        self.prompt_count = 0
        self.eval_count = count
        self.prompt_duration = (time2 - time1) if time2 else 0
        self.eval_duration = (time3 - time2) if time2 else 0
        if usage:
            if v := usage.get("prompt_tokens", None):
                self.prompt_count = int(v)
            if v := usage.get("completion_tokens", None):
                self.eval_count = int(v)
            if v := usage.get("prompt_time", None):
                self.prompt_duration = float(v)
            if v := usage.get("completion_time", None):
                self.eval_duration = float(v)
        self.prompt_rate = self.prompt_count / self.prompt_duration if self.prompt_duration > 0 else 0
        self.eval_rate = self.eval_count / self.eval_duration if self.eval_duration > 0 else 0

    def generate(self, prompt: str, history=None):
        """
        OpenAIにプロンプトを送信し、ストリーム応答を取得します。

        Args:
            prompt: OpenAIに送信するプロンプト文字列。
            history: OpenAIに送信する履歴のリスト。

        Yields:
            応答のチャンク文字列。
        """
        contents1 = [("user", prompt)]
        if history is None:
            contents = self.convert_history(contents1)
        else:
            # 履歴がある場合は、履歴を追加
            contents = self.convert_history(history + contents1)
        return self.chat(contents)

if __name__ == '__main__':
    test(Generator)

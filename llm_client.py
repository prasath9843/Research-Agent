import os
import json
import re
import time
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from openai import OpenAI
from config import settings

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    def __init__(self):
        self.fast_model = settings.FAST_MODEL
        self.strong_model = settings.STRONG_MODEL

    def _get_client(self) -> OpenAI:
        api_key = settings.NVIDIA_API_KEY or os.getenv("NVIDIA_API_KEY", "")
        base_url = settings.NVIDIA_BASE_URL or os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        return OpenAI(
            base_url=base_url,
            api_key=api_key if api_key else "dummy_key_for_init",
            timeout=30.0  # 30-second fast timeout to prevent long delays
        )

    def _clean_json_response(self, text: str) -> str:
        """Strips markdown code blocks and preambles from JSON response."""
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        return text

    def _repair_json(self, malformed_json: str) -> str:
        """Uses fast LLM to repair invalid JSON syntax."""
        repair_prompt = (
            "The following text was supposed to be a valid JSON string but has syntax errors. "
            "Fix the syntax and output ONLY the valid JSON string. Do not add explanations, preamble, or markdown formatting.\n\n"
            f"MALFORMED JSON:\n{malformed_json}"
        )
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.fast_model,
                messages=[
                    {"role": "system", "content": "You are a JSON syntax repair tool."},
                    {"role": "user", "content": repair_prompt}
                ],
                temperature=0.0
            )
            return self._clean_json_response(response.choices[0].message.content or "")
        except Exception as e:
            print(f"[LLMClient] Repair retry failed: {e}")
            return malformed_json

    def completion(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful research assistant.",
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2500
    ) -> str:
        selected_model = model or self.fast_model
        client = self._get_client()
        
        fallback_models = [
            selected_model,
            "meta/llama-3.1-8b-instruct",
            "meta/llama-3.2-3b-instruct"
        ]

        last_exception = None

        for attempt, current_model in enumerate(fallback_models):
            try:
                if attempt > 0:
                    print(f"[LLMClient] Fast retry completion with model '{current_model}' (Attempt {attempt+1}/3)...")

                response = client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                res_content = response.choices[0].message.content or ""
                if res_content.strip():
                    return res_content
            except Exception as err:
                last_exception = err
                err_msg = str(err)
                print(f"[LLMClient] Warning: Model '{current_model}' returned error: {err_msg}")
                continue

        if last_exception:
            raise last_exception
        raise RuntimeError("LLM completion failed across all fallback models.")

    def structured_output(
        self,
        prompt: str,
        response_model: Type[T],
        model: Optional[str] = None,
        max_retries: int = 2
    ) -> T:
        selected_model = model or self.fast_model

        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_prompt = (
            "You are a precise structured data extraction assistant. "
            "You MUST respond ONLY with a valid JSON object matching the JSON Schema provided. "
            "Do NOT include markdown formatting, preambles, or conversational commentary.\n\n"
            f"JSON SCHEMA:\n{schema_json}"
        )

        raw_response = self.completion(
            prompt=prompt,
            system_prompt=system_prompt,
            model=selected_model,
            temperature=0.1
        )

        cleaned_text = self._clean_json_response(raw_response)

        try:
            data_dict = json.loads(cleaned_text)
            return response_model.model_validate(data_dict)
        except Exception as first_error:
            print(f"[LLMClient] Initial JSON parse failed: {first_error}. Attempting repair retry...")
            repaired_text = self._repair_json(cleaned_text)
            try:
                data_dict = json.loads(repaired_text)
                return response_model.model_validate(data_dict)
            except Exception as second_error:
                raise ValueError(f"Failed to parse structured JSON after repair retry. Raw response:\n{raw_response}\nError: {second_error}")

llm_client = LLMClient()

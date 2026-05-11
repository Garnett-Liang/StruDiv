import requests
from openai import OpenAI

def call_llm(
    prompt: str,
    model_type: str,
    config: dict,
    temperature: float = 0.7
):
    """
    统一调用三大模型
    """

    # 1. DeepSeek API
    if model_type == "deepseek":
        api_key = config["api_key"]
        api_url = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        data = {
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 2000,
            "top_p": 0.95
        }

        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        res_json = response.json()
        return res_json["choices"][0]["message"]["content"].strip()

    # 2. Qwen API
    elif model_type == "qwen":
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )

        completion = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=False
        )
        return completion.choices[0].message.content.strip()

    # 3. MiniMax API
    elif model_type == "minimax":
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )

        completion = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=False
        )
        return completion.choices[0].message.content.strip()

    # 4. GLM API
    elif model_type == "glm":
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        completion = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=True
        )
        full_content = ""
        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
        return full_content.strip()
        

    # 5. Kimi API
    elif model_type == "kimi":
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        completion = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=False
        )
        return completion.choices[0].message.content.strip()

    else:
        raise ValueError(f"Unsupported model_type: {model_type}")

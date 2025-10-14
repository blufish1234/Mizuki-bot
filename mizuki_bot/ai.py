from openai import OpenAI


def Chat(model, question):
    client = OpenAI(
        # base_url="https://api.x.ai/v1",
        # api_key=XAIAPIKey,
    )

    completion = client.chat.completions.create(
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


def TranslateJpZht(text):
    client = OpenAI()
    response = client.responses.create(
        prompt={"id": "pmpt_685d33790e648193a4ea62fe73ee57c00eb21ac9521b57b2"},
        input=[{"role": "user", "content": [{"type": "input_text", "text": text}]}],
        reasoning={},
        max_output_tokens=2048,
        store=False,
    )
    return response.output_text

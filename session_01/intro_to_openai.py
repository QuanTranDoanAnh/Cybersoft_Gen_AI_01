from openai import OpenAI

# Khởi tạo session làm việc
client = OpenAI(
    api_key="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"
)

user_question = input()

response = client.chat.completions.create(
    model="gpt-5-mini",
    # Bên trong messages, vừa gửi đi req của user, vừa được dùng với những mục đích liên quan lưu trữ ngữ cảnh chat
    messages=[
        {"role": "system", "content": "Đây là một trợ lý AI"},
        {"role": "user", "content": user_question},
    ],
)

print(response.choices[0].message.content)

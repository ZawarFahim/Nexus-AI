import asyncio
from google import genai
from google.genai import types
import json
from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_weather",
            description="Get the weather for a location",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "location": types.Schema(type=types.Type.STRING, description="The city name")
                },
                required=["location"]
            )
        )
    ]
)

async def main():
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=[tool],
            temperature=0
        )
    )
    response = chat.send_message("What is the weather in Paris?")
    print("Response parts:", response.candidates[0].content.parts)
    if response.function_calls:
        print("Function calls:", response.function_calls)
        
        # mock response
        fc = response.function_calls[0]
        resp = chat.send_message([types.Part.from_function_response(
            name=fc.name,
            response={"weather": "Sunny, 25C"}
        )])
        print("Final response:", resp.text)

if __name__ == "__main__":
    asyncio.run(main())

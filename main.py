import argparse
import os
from google import genai
from dotenv import load_dotenv
from google.genai import types
from prompts import system_prompt
from call_function import available_functions
from call_function import call_function

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if api_key is None:
    raise RuntimeError("GEMINI_API_KEY not found.")

client = genai.Client(api_key=api_key)
parser = argparse.ArgumentParser(description="Chatbot")
parser.add_argument("user_prompt", type=str, help="User prompt")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()
messages: list[types.Content] = [
    types.Content(role="user", parts=[types.Part(text=args.user_prompt)])
]


def main():
    for i in range(20):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                tools=[available_functions],
                system_instruction=system_prompt,
                temperature=0
            ),
        )

        if response.usage_metadata is None:
            raise RuntimeError("no usage metadata returned from the API.")

        if args.verbose:
            print(f"Prompt tokens: {response.usage_metadata.prompt_token_count}")
            print(f"Response tokens: {response.usage_metadata.candidates_token_count}")

        if response.candidates:
            for candidate in response.candidates:
                messages.append(candidate.content)

        if response.function_calls:
            function_responses = []
            for function_call in response.function_calls:
                function_call_result = call_function(function_call, verbose=args.verbose)

                if not function_call_result.parts:
                    raise Exception("Empty parts list in function call result")

                function_response = function_call_result.parts[0].function_response
                if function_response is None:
                    raise Exception("No function_response in result")

                if function_response.response is None:
                    raise Exception("No response field in function_response")

                if args.verbose:
                    print(f"-> {function_call_result.parts[0].function_response.response}")

                function_responses.append(function_call_result.parts[0])

            messages.append(types.Content(role="user", parts=function_responses))
        else:
            print("Final response:")
            print(response.text)
            return

    print("Maximum iterations reached. No final response.")
    exit(1)


if __name__ == "__main__":
    main()

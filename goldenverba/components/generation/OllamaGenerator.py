import os

from wasabi import msg
import json
import requests
import aiohttp

from goldenverba.components.interfaces import Generator


class OllamaGenerator(Generator):
    def __init__(self):
        super().__init__()
        self.name = "OllamaGenerator"
        self.description = "Generator using a local running Ollama Model"
        self.requires_env = ["OLLAMA_URL","OLLAMA_MODEL"]
        self.streamable = True
        self.context_window = 3000

    async def generate_stream(
        self,
        queries: list[str],
        context: list[str],
        conversation: dict = None,
    ):
        """Generate a stream of response dicts based on a list of queries and list of contexts, and includes conversational context
        @parameter: queries : list[str] - List of queries
        @parameter: context : list[str] - List of contexts
        @parameter: conversation : dict - Conversational context
        @returns Iterator[dict] - Token response generated by the Generator in this format {system:TOKEN, finish_reason:stop or empty}.
        """

        url = os.environ.get("OLLAMA_URL", "")
        model = os.environ.get("OLLAMA_MODEL", "")
        if url == "":
            yield {
                    "message": "Missing Ollama URL",
                    "finish_reason": "stop",
                }

        url += "/api/chat"

        if conversation is None:
            conversation = {}
        messages = self.prepare_messages(queries, context, conversation)
        
        try:
            data = {
                "model": model,
                "messages": messages
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    async for line in response.content:
                        if line.strip():  # Ensure line is not just whitespace
                            json_data = json.loads(line.decode('utf-8'))  # Decode bytes to string then to JSON
                            message = json_data.get("message", {}).get("content", "")
                            finish_reason = "stop" if json_data.get("done", False) else ""

                            yield {
                                "message": message,
                                "finish_reason": finish_reason,
                            }
                        else:
                            yield {
                                "message": "",
                                "finish_reason": "stop",
                            }

        except Exception:
            raise

    def prepare_messages(
        self, queries: list[str], context: list[str], conversation: dict[str, str]
    ) -> dict[str, str]:
        """
        Prepares a list of messages formatted for a Retrieval Augmented Generation chatbot system, including system instructions, previous conversation, and a new user query with context.

        @parameter queries: A list of strings representing the user queries to be answered.
        @parameter context: A list of strings representing the context information provided for the queries.
        @parameter conversation: A list of previous conversation messages that include the role and content.

        @returns A list of message dictionaries formatted for the chatbot. This includes an initial system message, the previous conversation messages, and the new user query encapsulated with the provided context.

        Each message in the list is a dictionary with 'role' and 'content' keys, where 'role' is either 'system' or 'user', and 'content' contains the relevant text. This will depend on the LLM used.
        """
        messages = [
            {
                "role": "system",
                "content": self.system_message,
            }
        ]

        for message in conversation:
            messages.append({"role": message.type, "content": message.content})

        query = " ".join(queries)
        user_context = " ".join(context)

        messages.append(
            {
                "role": "user",
                "content": f"Please answer this query: '{query}' with this provided context: {user_context}",
            }
        )

        return messages

from openai import AzureOpenAI
import os
import logging
from errors import *
from utils.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        try:
            self.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
            self.api_key = os.getenv("AZURE_OPENAI_KEY")
            self.deployment_name = "gpt-4.1-nano"
            self.api_version = '2024-12-01-preview'

            self.client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                base_url=f"{self.api_base}/openai/deployments/{self.deployment_name}"
            )

            # System prompt for board document analysis
            self.system_prompt = SYSTEM_PROMPT

        except Exception as e:
            logger.error(e)
            raise CriticalInitializationError(f"Could not initialize OpenAI: {e}")

    def _stream_completion(self, prompt, context, chat_history=None):
        """
        Stream a completion given a prompt and context

        Args:
            prompt: The user's question
            context: The context from GroundX search
            chat_history: Optional list of previous messages

        Yields:
            Chunks of the response text
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                }
            ]

            # Add chat history if provided
            if chat_history:
                messages.extend(chat_history)

            # Add the context and current query
            messages.append({
                "role": "user",
                "content": f"Here is the relevant context from the board documents:\n\n{context}\n\nBased on this context, please answer the following question: {prompt}"
            })

            stream = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                stream=True,
                max_completion_tokens=800,
                temperature=0.7,  # Lower for more factual responses
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error in stream_completion: {str(e)}")
            yield f"Error generating response: {str(e)}"

    def stream_completion(self, prompt, context, chat_history=None):
        """
        Stream a completion given a prompt and context

        Args:
            prompt: The user's question
            context: The context from GroundX search
            chat_history: Optional list of previous messages

        Yields:
            Chunks of the response text
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                }
            ]

            # Add chat history if provided
            if chat_history:
                messages.extend(chat_history)

            # Add the context and current query
            messages.append({
                "role": "user",
                "content": f"Here is the relevant context from the board documents:\n\n{context}\n\nBased on this context, please answer the following question: {prompt}"
            })

            # Debug: log the request
            logger.info(f"Streaming completion with model: {self.deployment_name}")

            stream = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                stream=True,
                max_completion_tokens=800,
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            for chunk in stream:
                # Better error handling for chunk structure
                if chunk and hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                        if choice.delta.content is not None:
                            cleaned_content = choice.delta.content.replace('$', '\$') # Required to prevent streamlit markdown thinking $ are equations
                            yield cleaned_content
                # Skip chunks that don't have content (like the first chunk)

        except Exception as e:
            logger.error(f"Error in stream_completion: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            yield f"Error generating response: {str(e)}"

    def get_completion(self, prompt, context, chat_history=None):
        """
        Get a non-streaming completion

        Args:
            prompt: The user's question
            context: The context from GroundX search
            chat_history: Optional list of previous messages

        Returns:
            The complete response text
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                }
            ]

            # Add chat history if provided
            if chat_history:
                messages.extend(chat_history)

            # Add the context and current query
            messages.append({
                "role": "user",
                "content": f"Here is the relevant context from the board documents:\n\n{context}\n\nBased on this context, please answer the following question: {prompt}"
            })

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_completion_tokens=800,
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error in get_completion: {str(e)}")
            return f"Error generating response: {str(e)}"
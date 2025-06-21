from openai import AzureOpenAI
import os
import logging
from errors import *

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
            self.system_prompt = (
                "You are a chatbot in the role of expert on the documents stored by the company for Board of Directors. "
                "Your only focus is on understanding those documents at a factual level. "
                "You can make inferences directly related to the content of the documents: noting trends or gaps or material observations. "
                "Format your responses using markdown for better readability - use sub-headings (###), bullet points (-), bold (**text**), and other formatting as appropriate to structure information clearly. "
                "Avoid equation formats in markdown that can render text in odd ways. "
                "IMPORTANT: You do not return technical details like file_ids or pipeline names as you only deal in content, inference, and filenames. "
                "IMPORTANT: You do NOT bring other knowledge or inferences to responses beyond the document and chat context. "
                "IMPORTANT: You do NOT respond with general answers on theory or concepts or guesses outside of these documents. "
                "IMPORTANT: If you don't have the relevant information for a question, don't make up content to fill in gaps. Just say that you can't find that information in the corpus. "
                "IMPORTANT: The context you receive will describe documents or pages as if someone is looking at them. You shouldn't respond that way. You should take that information and articulate it as if it is knowledge you have. Not something you are reading."
                "If a question asks you to speculate beyond the scope discussed above, simply say 'Answers to that question are outside the scope of my function'."
            )

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
                            cleaned_content = choice.delta.content.replace('$', '\\$')
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
# context_manager.py
# This module is responsible for managing the conversation history to keep the LLM's
# context window clean and for identifying messages that should be moved to long-term memory.
# It is adapted from Damien AI's original implementation.

import json

class ContextManager:
    """
    Manages the conversation history to provide a focused context for the LLM
    and identifies messages that have overflowed the active context window.
    """

    def __init__(self, full_history: list, max_tokens: int = 2048):
        """
        Initializes the ContextManager.

        Args:
            full_history (list): The entire list of message dictionaries.
            max_tokens (int): The maximum number of tokens for the short-term context window.
        """
        self.full_history = full_history
        self.max_tokens = max_tokens

    def _count_tokens(self, message: dict) -> int:
        """
        A simple approximation for counting tokens in a message object.
        A more accurate tokenizer could be used for higher precision.
        """
        # A rough estimate is that one token is about 4 characters.
        return len(json.dumps(message)) // 4

    def get_current_context(self) -> list:
        """
        Constructs the short-term context that fits within the token limit,
        starting from the most recent messages.

        Returns:
            list: A list of message dictionaries representing the current context.
        """
        current_context = []
        current_tokens = 0
        # Iterate backwards from the most recent message to prioritize them
        for message in reversed(self.full_history):
            message_tokens = self._count_tokens(message)
            if current_tokens + message_tokens <= self.max_tokens:
                # Prepend to maintain the correct chronological order
                current_context.insert(0, message)
                current_tokens += message_tokens
            else:
                # Stop as soon as the window is full
                break
        
        return current_context

    def get_overflow_chunks(self) -> list:
        """
        Identifies messages that are no longer in the current context window
        and marks them as saved to prevent being processed again.

        Returns:
            list: A list of overflow message dictionaries to be saved to long-term memory.
        """
        overflow_chunks = []
        current_context_messages = self.get_current_context()
        
        # Create a set of the content from the current context for efficient checking
        current_context_contents = {msg['content'] for msg in current_context_messages}

        for message in self.full_history:
            # A message is an overflow chunk if:
            # 1. Its content is not in the current active context.
            # 2. It has not already been marked as 'is_saved'.
            if message.get('content') not in current_context_contents and not message.get('is_saved', False):
                overflow_chunks.append(message)
                # IMPORTANT: We modify the original message in the history list in-place.
                # This marks it as "processed" for future runs of this check.
                message['is_saved'] = True
        
        if overflow_chunks:
            print(f"Identified {len(overflow_chunks)} new message chunks for long-term memory.")
            
        return overflow_chunks

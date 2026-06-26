from .orchestrator import AIOrchestrator


class Summarizer:

    def __init__(self):
        self.orchestrator = AIOrchestrator()

    def summarize(self, text: str, max_words: int = 60):
        """
        Generate a summary of the text using Claude AI.
        Falls back to simple word truncation if Claude is not configured.
        
        Args:
            text: Input text to summarize
            max_words: Maximum words in summary
            
        Returns:
            Generated summary
        """
        if self.orchestrator:
            try:
                summary = self.orchestrator.summarize(text, max_words)
                return summary
            except Exception as e:
                print(f"Claude summarization failed: {e}")
        
        # Fallback to simple summarization
        words = text.split()
        summary = " ".join(words[:max_words])
        return summary + ("..." if len(words) > max_words else "")

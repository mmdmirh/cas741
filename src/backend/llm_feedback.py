class LLMFeedbackGenerator:
    """A stub generator to provide simple text feedback when the LLM is not in use."""
    def __init__(self, use_api=False):
        self.use_api = use_api

    def generate_feedback(self, error_record):
        # Convert the error type back to a human-readable sentence
        errors = error_record.get("errors", [])
        if not errors:
            return ""
        
        # Priority to the first error detected
        error = errors[0]
        error_type = error.get("type", "unknown")
        
        # Simple mapping for local feedback
        mapping = {
            "elbow_stability": "Keep your elbow stable!",
            "reach_full_range": "Reach full range of motion!",
            "go_deeper": "Go deeper in your squat!",
            "adjust_camera_to_show_full_body": "Adjust camera to see your whole body",
            "great_curl": "Great curl!",
            "good_depth": "Good depth!",
        }
        
        return mapping.get(error_type, error_type.replace("_", " ").capitalize() + "!")

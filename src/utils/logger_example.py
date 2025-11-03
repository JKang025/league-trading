"""Example usage of the logger with JSON format.

This file demonstrates how to use the logger and what the JSON output looks like.
"""

from src.utils.logger import get_logger, log


# Example 1: Simple usage with the convenience function
def example_simple():
    """Basic logging examples."""
    # Simple message
    log("Processing started")
    
    # Different log levels
    log("This is a debug message", level="DEBUG")
    log("This is an info message", level="INFO")
    log("This is a warning", level="WARNING")
    log("This is an error", level="ERROR")
    
    # With additional context (these become JSON fields!)
    log("Fetching match data", match_id="12345", region="NA1", user_id="abc123")


# Example 2: Using the logger instance directly
def example_logger_instance():
    """Using get_logger() for more control."""
    logger = get_logger()
    
    # Simple logging
    logger.info("Starting data pipeline")
    
    # Logging with structured data (JSON fields)
    logger.info(
        "Match fetched successfully",
        match_id="EUW1_1234567890",
        duration_ms=234,
        status_code=200,
    )
    
    # Logging errors with context
    logger.error(
        "API request failed",
        endpoint="/lol/match/v5/matches/EUW1_1234567890",
        status_code=429,
        retry_after=60,
        error_type="RateLimitError",
    )


# Example 3: Logging with complex data structures
def example_structured_data():
    """Logging with dictionaries and lists (will be JSON-serialized)."""
    logger = get_logger()
    
    # Log with dictionary data
    match_data = {
        "match_id": "EUW1_1234567890",
        "duration": 1800,
        "winner": "blue",
        "game_mode": "CLASSIC",
    }
    logger.info("Match processed", match_data=match_data)
    
    # Log with list data
    participants = ["player1", "player2", "player3"]
    logger.info("Participants fetched", count=len(participants), participants=participants)
    
    # Log with nested structures
    logger.info(
        "Match analysis complete",
        match_id="EUW1_1234567890",
        statistics={
            "avg_kda": 2.5,
            "total_kills": 25,
            "game_length": 1800,
        },
        teams=["blue", "red"],
    )


# Example 4: Error logging with exceptions
def example_error_logging():
    """Logging exceptions and errors."""
    logger = get_logger()
    
    try:
        # Some code that might fail
        result = 10 / 0
    except ZeroDivisionError as e:
        # Log exception with context
        logger.exception(
            "Division by zero error",
            operation="divide",
            numerator=10,
            denominator=0,
        )
    
    # Log errors without exceptions
    logger.error(
        "Failed to fetch match",
        match_id="EUW1_1234567890",
        reason="match_not_found",
        status_code=404,
    )


# Example 5: Different logger configurations
def example_configurations():
    """Different ways to configure the logger."""
    
    # Default: JSON format, logs to stdout, logs/ in project root
    logger1 = get_logger()
    logger1.info("Default configuration")
    
    # JSON format, no stdout output
    logger2 = get_logger(log_to_stdout=False)
    logger2.info("No stdout output", data="This only goes to file")
    
    # Human-readable format (not JSON)
    logger3 = get_logger(json_format=False)
    logger3.info("Human-readable format", data="This is plain text")
    
    # Custom log directory
    logger4 = get_logger(log_dir="custom_logs")
    logger4.info("Custom log directory", location="custom_logs/")


# Example 6: What the JSON output looks like
def explain_json_format():
    """
    Explanation of JSON format:
    
    When json_format=True (default), each log entry in the file is a JSON object like:
    
    {
        "text": "Your message here",
        "record": {
            "elapsed": {...},
            "exception": null,
            "extra": {
                "file": "src/utils/logger_example.py"
            },
            "file": {
                "name": "logger_example.py",
                "path": "/full/path/to/logger_example.py"
            },
            "function": "example_simple",
            "level": {
                "icon": "ℹ️",
                "name": "INFO",
                "no": 20
            },
            "line": 15,
            "message": "Your message here",
            "module": "logger_example",
            "name": "root",
            "process": {
                "id": 12345,
                "name": "MainProcess"
            },
            "thread": {
                "id": 140123456789,
                "name": "MainThread"
            },
            "time": {
                "repr": "2024-01-15 10:30:45.123456+00:00",
                "timestamp": 1705315845.123456
            }
        }
    }
    
    Any **kwargs you pass (like match_id, user_id, etc.) will appear in the "extra" field.
    
    Example: log("Fetching match", match_id="123", region="NA1")
    
    Results in:
    {
        "text": "Fetching match",
        "record": {
            ...
            "extra": {
                "file": "src/your_file.py",
                "match_id": "123",      # <-- Your custom field
                "region": "NA1"        # <-- Your custom field
            },
            ...
        }
    }
    """


if __name__ == "__main__":
    print("Running logger examples...")
    print("\n=== Example 1: Simple Usage ===")
    example_simple()
    
    print("\n=== Example 2: Logger Instance ===")
    example_logger_instance()
    
    print("\n=== Example 3: Structured Data ===")
    example_structured_data()
    
    print("\n=== Example 4: Error Logging ===")
    example_error_logging()
    
    print("\n=== Example 5: Configurations ===")
    example_configurations()
    
    print("\n✅ Examples complete! Check logs/app_*.log for JSON output")
    print("📝 See explain_json_format() docstring for JSON structure details")


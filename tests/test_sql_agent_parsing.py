import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Append the absolute path of the 'app' directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

import ollama
from AgentSQL import SQLGenerationAgent

# Mock schema text matching your actual database tables
MOCK_SCHEMA_DOC = "- Table: public_read_only.products -> Columns: [id (integer), product_name (character varying), product_price (numeric), stock_volume (integer)]"


@pytest.fixture
def mock_sql_agent():
    """Provides a SQLGenerationAgent with mocked dependencies."""
    mock_client = MagicMock(spec=ollama.Client)

    with patch('AgentSQL.SchemaDiscoverer') as MockDiscoverer:
        instance = MockDiscoverer.return_value
        instance.get_active_schema_documentation.return_value = MOCK_SCHEMA_DOC

        agent = SQLGenerationAgent(client=mock_client, target_schema="public_read_only")
        yield agent


@pytest.mark.parametrize(
    "model_output, expected_sql",
    [
        # Scenario 1: Clean, valid JSON object (Typical Qwen behavior)
        (
                '{"sql_query": "SELECT product_name, SUM(product_price * stock_volume) FROM public_read_only.products GROUP BY product_name;"}',
                "SELECT product_name, SUM(product_price * stock_volume) FROM public_read_only.products GROUP BY product_name;"
        ),
        # Scenario 2: JSON wrapped inside a Markdown Code Fence (Typical Gemma quirk)
        (
                '```json\n{"sql_query": "SELECT product_name FROM public_read_only.products"}\n```',
                "SELECT product_name FROM public_read_only.products"
        ),
        # Scenario 3: Aggressive Markdown formatting inside the JSON value field
        (
                '{\n  "sql_query": "```sql\\nSELECT product_name, stock_volume FROM public_read_only.products\\n```"\n}',
                "SELECT product_name, stock_volume FROM public_read_only.products"
        ),
        # Scenario 4: Raw SQL block embedded inside standard text without direct valid JSON
        (
                "Here is the database query requested:\n```sql\nSELECT * FROM public_read_only.products LIMIT 5;\n```",
                "SELECT * FROM public_read_only.products LIMIT 5;"
        ),
        # Scenario 5: Semicolon validation and internal newline formatting
        (
                '{"sql_query": "SELECT\\nproduct_name\\nFROM\\npublic_read_only.products;"}',
                "SELECT product_name FROM public_read_only.products;"
        )
    ],
    ids=["clean_json", "markdown_wrapped_json", "nested_markdown_in_json", "raw_markdown_fence", "newline_formatting"]
)
def test_successful_sql_extractions(mock_sql_agent, model_output, expected_sql):
    """Verifies that diverse LLM output variations correctly return clean SQL text strings."""
    user_question = "what is the total value of the whole stock for each product category"

    with patch('AgentSQL._cached_llm_sql_call', return_value=model_output):
        result = mock_sql_agent.generate_query(user_question, model_name="gemma4:e2b")

        assert result is not None, f"Failed to extract SQL from output: {model_output}"
        assert result == expected_sql


@pytest.mark.parametrize(
    "malformed_output",
    [
        ('{"error": "I cannot answer this question."}'),
        ("I am sorry, but I do not have access to structural matrices."),
        ("```sql\nDROP TABLE public_read_only.products;\n```"),
        ("")
    ],
    ids=["json_wrong_key", "conversational_refusal", "non_select_statement", "empty_response"]
)
def test_extraction_failures_and_edge_cases(mock_sql_agent, malformed_output):
    """Verifies that non-compliant or empty structures correctly bubble up as None."""
    user_question = "what is the total value of the whole stock for each product category"

    with patch('AgentSQL._cached_llm_sql_call', return_value=malformed_output):
        result = mock_sql_agent.generate_query(user_question, model_name="gemma4:e2b")

        if result:
            assert "select" in result.lower(), "Extracted statement must be a safe SELECT clause"
        else:
            assert result is None

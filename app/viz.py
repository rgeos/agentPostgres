class VisualizationHelper:
    """Detects analytical patterns in database outputs and structures visualization data."""

    # Inside viz.py -> VisualizationHelper
    @staticmethod
    def generate_chart_metadata(raw_data: list) -> dict | None:
        if not raw_data or not isinstance(raw_data, list) or len(raw_data) < 1:
            return None

        first_row = raw_data[0]
        if not isinstance(first_row, dict):
            return None

        numeric_keys = [
            k for k, v in first_row.items() if isinstance(v, (int, float)) and k != "id"
        ]
        string_keys = [k for k, v in first_row.items() if isinstance(v, str)]

        # Scenario A: Aggregate counts or single metrics (e.g., [ {'sum': 292} ])
        if len(raw_data) == 1 and len(numeric_keys) >= 1:
            key_name = numeric_keys[0]
            return {
                "type": "metric",
                "label": key_name.replace("_", " ").title(),
                "value": raw_data[0][key_name],
            }

        # Scenario B: Multi-row category datasets
        if len(raw_data) > 1 and len(numeric_keys) >= 1:
            data_key = numeric_keys[0]

            # FALLBACK: If the LLM didn't select a string label, use item index numbers
            if len(string_keys) >= 1:
                label_key = string_keys[0]
                labels = [str(row[label_key]) for row in raw_data]
            else:
                labels = [f"Item {i + 1}" for i in range(len(raw_data))]

            values = [float(row[data_key]) for row in raw_data]

            chart_type = "bar"
            if len(string_keys) >= 1 and any(
                x in string_keys[0].lower() for x in ["date", "month", "year"]
            ):
                chart_type = "line"
            elif len(labels) <= 4:
                chart_type = "pie"

            return {
                "type": "chart",
                "chart_style": chart_type,
                "data": {
                    "labels": labels,
                    "datasets": [
                        {"label": data_key.replace("_", " ").title(), "data": values}
                    ],
                },
            }

        return None

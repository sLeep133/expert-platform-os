import json
import re


def parse_feishu_filter(filter_formula):
    """
    Parse natural filter expressions into Feishu Bitable JSON filter.
    Supports:
      - CurrentValue["Field"] == "Value"
      - CurrentValue['Field'] == 'Value'
      - Field == Value
      - Field: Value
      - Raw JSON string (passed through)
    Returns JSON string or None.
    """
    if not filter_formula:
        return None

    # Already JSON?
    try:
        json.loads(filter_formula)
        return filter_formula
    except json.JSONDecodeError:
        pass

    # Match CurrentValue["Field"] == "Value"  or  CurrentValue['Field'] == 'Value'
    m = re.search(r'CurrentValue\[["\']([^"\']+)["\']\]\s*==\s*["\']([^"\']+)["\']', filter_formula)
    if m:
        field, value = m.groups()
        return json.dumps({
            "conjunction": "and",
            "conditions": [{"field_name": field, "operator": "is", "value": [value]}]
        }, ensure_ascii=False)

    # Match Field == "Value" or Field == Value
    m = re.search(r'([\w\u4e00-\u9fff]+)\s*==\s*["\']?([^"\',\s]+)["\']?', filter_formula)
    if m:
        field, value = m.groups()
        return json.dumps({
            "conjunction": "and",
            "conditions": [{"field_name": field, "operator": "is", "value": [value]}]
        }, ensure_ascii=False)

    # Match Field: Value
    m = re.search(r'([\w\u4e00-\u9fff]+)\s*[:=]\s*["\']?([^"\',\s]+)["\']?', filter_formula)
    if m:
        field, value = m.groups()
        return json.dumps({
            "conjunction": "and",
            "conditions": [{"field_name": field, "operator": "is", "value": [value]}]
        }, ensure_ascii=False)

    # Fallback: return as-is and let Feishu complain
    return filter_formula

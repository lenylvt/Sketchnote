"""
Auto-repair utilities for common JSON/API errors.

Provides automatic error detection and correction for malformed JSON payloads,
encoding issues, syntax errors, and other common API problems.

License: MIT
"""

import json
import re
import logging
from typing import Any, Dict, Tuple, Optional
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class AutoRepair:
    """Automatic error detection and repair for API payloads."""
    
    @staticmethod
    def repair_json(raw_data: str) -> Tuple[bool, str, Optional[str]]:
        """
        Attempt to repair malformed JSON.
        
        Args:
            raw_data: Raw JSON string (potentially malformed)
            
        Returns:
            Tuple of (success, repaired_json, error_message)
        """
        if not raw_data or not isinstance(raw_data, str):
            return False, raw_data, "Empty or invalid input"
        
        original = raw_data
        repairs_applied = []
        
        # Try parsing as-is first
        try:
            json.loads(raw_data)
            return True, raw_data, None
        except json.JSONDecodeError as e:
            logger.info(f"JSON parsing failed: {e}. Attempting auto-repair...")
        
        # Repair 1: Strip BOM and invisible characters
        if raw_data.startswith('\ufeff'):
            raw_data = raw_data.lstrip('\ufeff')
            repairs_applied.append("Removed BOM")
        
        # Repair 2: Remove control characters
        raw_data = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw_data)
        
        # Repair 3: Fix common trailing comma issues
        raw_data = re.sub(r',(\s*[}\]])', r'\1', raw_data)
        if raw_data != original:
            repairs_applied.append("Removed trailing commas")
        
        # Repair 4: Fix missing commas between properties
        raw_data = re.sub(r'"\s*\n\s*"', '",\n  "', raw_data)
        raw_data = re.sub(r'(\d)\s*\n\s*"', r'\1,\n  "', raw_data)
        raw_data = re.sub(r'(true|false)\s*\n\s*"', r'\1,\n  "', raw_data)
        
        # Repair 5: Fix unescaped quotes in strings
        # Match strings and escape internal quotes
        def escape_quotes(match):
            content = match.group(1)
            # Don't escape already escaped quotes
            content = re.sub(r'(?<!\\)"', r'\\"', content)
            return f'"{content}"'
        
        # Be careful with this - only apply to obvious string values
        raw_data = re.sub(r'"([^"]*(?:\\"[^"]*)*)"', escape_quotes, raw_data)
        
        # Repair 6: Fix single quotes to double quotes (common mistake)
        # Only outside of already-quoted strings
        raw_data = re.sub(r"'([^']*)':", r'"\1":', raw_data)
        
        # Repair 7: Remove trailing content after valid JSON
        # Find the last closing brace/bracket
        bracket_depth = 0
        brace_depth = 0
        last_valid_pos = -1
        
        for i, char in enumerate(raw_data):
            if char == '{':
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
            elif char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1
            
            if brace_depth == 0 and bracket_depth == 0 and i > 0:
                if raw_data[i-1] in '}]':
                    last_valid_pos = i
                    break
        
        if last_valid_pos > 0 and last_valid_pos < len(raw_data) - 1:
            raw_data = raw_data[:last_valid_pos]
            repairs_applied.append("Removed trailing content")
        
        # Repair 8: Fix missing closing braces/brackets
        brace_count = raw_data.count('{') - raw_data.count('}')
        bracket_count = raw_data.count('[') - raw_data.count(']')
        
        if brace_count > 0:
            raw_data += '}' * brace_count
            repairs_applied.append(f"Added {brace_count} closing brace(s)")
        
        if bracket_count > 0:
            raw_data += ']' * bracket_count
            repairs_applied.append(f"Added {bracket_count} closing bracket(s)")
        
        # Repair 9: Fix newlines in strings (convert to \n)
        raw_data = re.sub(r':\s*"([^"]*)\n([^"]*)"', r': "\1\\n\2"', raw_data)
        
        # Repair 10: Remove comments (not valid JSON but common)
        raw_data = re.sub(r'//[^\n]*\n', '\n', raw_data)
        raw_data = re.sub(r'/\*.*?\*/', '', raw_data, flags=re.DOTALL)
        
        # Try parsing repaired JSON
        try:
            parsed = json.loads(raw_data)
            logger.info(f"✓ JSON repaired successfully. Repairs: {', '.join(repairs_applied)}")
            return True, raw_data, None
        except json.JSONDecodeError as e:
            error_msg = f"Could not repair JSON after {len(repairs_applied)} attempts: {str(e)}"
            logger.warning(error_msg)
            return False, raw_data, error_msg
    
    @staticmethod
    def repair_document_structure(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], list]:
        """
        Repair common document structure issues.
        
        Args:
            data: Parsed JSON document
            
        Returns:
            Tuple of (success, repaired_data, repairs_applied)
        """
        repairs = []
        
        # Ensure meta exists
        if "meta" not in data:
            data["meta"] = {}
            repairs.append("Added missing 'meta' object")
        
        # Ensure blocks exists and is a list
        if "blocks" not in data:
            data["blocks"] = []
            repairs.append("Added missing 'blocks' array")
        elif not isinstance(data["blocks"], list):
            data["blocks"] = [data["blocks"]]
            repairs.append("Converted 'blocks' to array")
        
        # Fix block structure issues
        fixed_blocks = []
        for i, block in enumerate(data.get("blocks", [])):
            if not isinstance(block, dict):
                repairs.append(f"Skipped invalid block #{i} (not an object)")
                continue
            
            # Ensure block has type
            if "type" not in block:
                # Try to infer type
                if "level" in block and "text" in block:
                    block["type"] = "heading"
                    repairs.append(f"Inferred block #{i} type as 'heading'")
                elif "text" in block:
                    block["type"] = "paragraph"
                    repairs.append(f"Inferred block #{i} type as 'paragraph'")
                elif "latex" in block:
                    block["type"] = "formula"
                    repairs.append(f"Inferred block #{i} type as 'formula'")
                elif "content" in block and isinstance(block["content"], list):
                    # Check if content is array of blocks (card) or string (code)
                    if block["content"] and isinstance(block["content"], list) and isinstance(block["content"][0], dict):
                        block["type"] = "card"
                        repairs.append(f"Inferred block #{i} type as 'card'")
                    else:
                        block["type"] = "code"
                        repairs.append(f"Inferred block #{i} type as 'code'")
                elif "content" in block:
                    block["type"] = "code"
                    repairs.append(f"Inferred block #{i} type as 'code'")
                else:
                    repairs.append(f"Skipped block #{i} (cannot infer type)")
                    continue
            
            # Fix text fields (ensure they're arrays of RichText)
            if "text" in block:
                if isinstance(block["text"], str):
                    block["text"] = [{"text": block["text"]}]
                    repairs.append(f"Converted block #{i} text to RichText array")
                elif isinstance(block["text"], list):
                    fixed_text = []
                    for j, span in enumerate(block["text"]):
                        if isinstance(span, str):
                            fixed_text.append({"text": span})
                            repairs.append(f"Converted block #{i} span #{j} to RichText")
                        elif isinstance(span, dict) and "text" in span:
                            fixed_text.append(span)
                        else:
                            repairs.append(f"Skipped invalid span in block #{i}")
                    block["text"] = fixed_text
            
            # Fix heading levels
            if block.get("type") == "heading":
                if "level" not in block:
                    block["level"] = 1
                    repairs.append(f"Added default level 1 to heading block #{i}")
                elif not isinstance(block["level"], int) or block["level"] not in [1, 2, 3]:
                    block["level"] = 1
                    repairs.append(f"Fixed invalid heading level in block #{i}")
            
            # Fix formula blocks
            if block.get("type") == "formula":
                if "latex" not in block:
                    repairs.append(f"Skipped formula block #{i} (missing latex)")
                    continue
            
            # Fix list blocks
            if block.get("type") == "list":
                if "variant" not in block:
                    block["variant"] = "bullet"
                    repairs.append(f"Added default variant to list block #{i}")
                if "items" not in block:
                    block["items"] = []
                    repairs.append(f"Added empty items to list block #{i}")
            
            fixed_blocks.append(block)
        
        data["blocks"] = fixed_blocks
        
        return True, data, repairs
    
    @staticmethod
    def repair_encoding(raw_bytes: bytes) -> Tuple[bool, str, Optional[str]]:
        """
        Attempt to decode bytes with various encodings.
        
        Args:
            raw_bytes: Raw byte data
            
        Returns:
            Tuple of (success, decoded_string, error_message)
        """
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                decoded = raw_bytes.decode(encoding)
                logger.info(f"Successfully decoded with {encoding}")
                return True, decoded, None
            except (UnicodeDecodeError, AttributeError):
                continue
        
        error_msg = f"Could not decode with any encoding: {encodings}"
        logger.warning(error_msg)
        return False, "", error_msg
    
    @staticmethod
    def auto_fix_validation_error(data: Dict[str, Any], error: ValidationError) -> Tuple[bool, Dict[str, Any], list]:
        """
        Attempt to fix Pydantic validation errors automatically.
        
        Args:
            data: Document data that failed validation
            error: Pydantic validation error
            
        Returns:
            Tuple of (success, fixed_data, repairs_applied)
        """
        repairs = []
        errors = error.errors()
        
        for err in errors:
            loc = err['loc']
            err_type = err['type']
            
            # Fix missing required fields
            if err_type == 'missing':
                # Navigate to parent and add default
                target = data
                for key in loc[:-1]:
                    if isinstance(key, int):
                        if isinstance(target, list) and key < len(target):
                            target = target[key]
                        else:
                            break
                    else:
                        target = target.get(key, {})
                
                missing_field = loc[-1]
                
                # Add appropriate defaults
                if missing_field == "text":
                    target[missing_field] = [{"text": ""}]
                    repairs.append(f"Added default text to {'.'.join(map(str, loc))}")
                elif missing_field == "type":
                    target[missing_field] = "paragraph"
                    repairs.append(f"Added default type to {'.'.join(map(str, loc))}")
                elif missing_field == "level":
                    target[missing_field] = 1
                    repairs.append(f"Added default level to {'.'.join(map(str, loc))}")
                elif missing_field == "latex":
                    target[missing_field] = ""
                    repairs.append(f"Added empty latex to {'.'.join(map(str, loc))}")
            
            # Fix invalid literal values
            elif err_type.startswith('literal_error'):
                target = data
                for key in loc[:-1]:
                    if isinstance(key, int) and isinstance(target, list):
                        target = target[key]
                    else:
                        target = target.get(key, {})
                
                field = loc[-1]
                if field == "type":
                    # Default to paragraph for unknown types
                    target[field] = "paragraph"
                    repairs.append(f"Changed invalid type to 'paragraph' at {'.'.join(map(str, loc))}")
        
        return len(repairs) > 0, data, repairs


def create_repair_summary(repairs: list) -> str:
    """Create a human-readable summary of repairs."""
    if not repairs:
        return "No repairs needed"
    
    return f"{len(repairs)} repair(s): " + "; ".join(repairs)

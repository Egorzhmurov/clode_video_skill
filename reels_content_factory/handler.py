"""Handler for routing a Claude Reels blueprint to production services."""

import json
from pathlib import Path
from typing import Any, Dict


BLOCK_NAMES = ("hook_block", "dynamic_body_block", "cta_block")
BLOCK_FIELDS = (
    "on_screen_text",
    "elevenlabs_voice_prompt",
    "veo3_video_prompt_en",
    "bootstrap_ui_html",
    "after_effects_motion",
)


def _extract_tool_input(claude_tool_response: dict) -> Dict[str, Any]:
    """Accept either a tool input dictionary or an Anthropic Messages response."""
    direct_input = claude_tool_response.get("input")
    if isinstance(direct_input, dict):
        return direct_input

    content = claude_tool_response.get("content")
    if isinstance(content, list):
        for item in content:
            if (
                isinstance(item, dict)
                and item.get("type") == "tool_use"
                and item.get("name") == "generate_reels_blueprint"
            ):
                tool_input = item.get("input")
                if isinstance(tool_input, dict):
                    return tool_input

    if all(name in claude_tool_response for name in BLOCK_NAMES):
        return claude_tool_response

    raise ValueError(
        "No generate_reels_blueprint tool input found in the Claude response."
    )


def handle_reels_generation(claude_tool_response: dict) -> Dict[str, Any]:
    """Validate blueprint blocks, save render specs, and return routing payload."""
    tool_input = _extract_tool_input(claude_tool_response)
    blocks: Dict[str, Dict[str, str]] = {}

    for block_name in BLOCK_NAMES:
        block = tool_input.get(block_name)
        if not isinstance(block, dict):
            raise ValueError(f"{block_name} must be an object.")

        missing_fields = [
            field for field in BLOCK_FIELDS if not isinstance(block.get(field), str)
        ]
        if missing_fields:
            raise ValueError(
                f"{block_name} must contain string values for: "
                + ", ".join(missing_fields)
            )
        blocks[block_name] = {field: block[field] for field in BLOCK_FIELDS}

    render_specs = {
        block_name: {
            "bootstrap_ui_html": block["bootstrap_ui_html"],
            "after_effects_motion": block["after_effects_motion"],
        }
        for block_name, block in blocks.items()
    }
    output_path = Path(__file__).with_name("render_specs.json")
    with output_path.open("w", encoding="utf-8") as render_specs_file:
        json.dump(render_specs, render_specs_file, ensure_ascii=False, indent=2)
        render_specs_file.write("\n")

    # Route each block's veo3_video_prompt_en to the configured VEO 3 client.
    # Example: veo3_client.generate(prompt=block["veo3_video_prompt_en"])
    # Route each block's elevenlabs_voice_prompt to the configured ElevenLabs client.
    # Example: elevenlabs_client.generate(prompt=block["elevenlabs_voice_prompt"])
    return {
        "topic": tool_input.get("topic"),
        "blocks": blocks,
        "render_specs_path": str(output_path),
    }

python3 -c "
with open('script_generator.py', 'r') as f:
    content = f.read()

old = '''    raw = message.content[0].text.strip()
    # Strip markdown fences if present (safety net)
    if raw.startswith(\"\`\`\`\"):
        raw = raw.split(\"\\n\", 1)[1].rsplit(\"\`\`\`\", 1)[0].strip()
    script_data = json.loads(raw)
    required_keys = [\"open_fragment\",\"intro\",\"act_1\",\"act_2\",\"act_3\",\"cutoff_line\",\"caption\"]
    missing = [k for k in required_keys if k not in script_data]
    if missing:
        raise ValueError(f\"Script JSON missing keys: {missing}\")
    return script_data'''

new = '''    raw = message.content[0].text.strip()
    if raw.startswith(\"\`\`\`\"):
        raw = raw.split(\"\\n\", 1)[1].rsplit(\"\`\`\`\", 1)[0].strip()
    # Retry up to 3 times if JSON is malformed
    for attempt in range(3):
        try:
            script_data = json.loads(raw)
            break
        except json.JSONDecodeError:
            if attempt < 2:
                log.warning(f\"JSON parse failed (attempt {attempt+1}), retrying...\")
                message = client.messages.create(
                    model      = \"claude-sonnet-4-5\",
                    max_tokens = 1500,
                    system     = SYSTEM_PROMPT,
                    messages   = [{\"role\": \"user\", \"content\": user_prompt}],
                )
                raw = message.content[0].text.strip()
                if raw.startswith(\"\`\`\`\"):
                    raw = raw.split(\"\\n\", 1)[1].rsplit(\"\`\`\`\", 1)[0].strip()
            else:
                raise
    required_keys = [\"open_fragment\",\"intro\",\"act_1\",\"act_2\",\"act_3\",\"cutoff_line\",\"caption\"]
    missing = [k for k in required_keys if k not in script_data]
    if missing:
        raise ValueError(f\"Script JSON missing keys: {missing}\")
    return script_data'''

content = content.replace(old, new)
with open('script_generator.py', 'w') as f:
    f.write(content)
print('Done')
"
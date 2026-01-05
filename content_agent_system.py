import json
import os
from datetime import datetime

MEMORY_FILE = "content_agent_memory.json"

agent = {
    "name": "Alpha",
    "role": "Content Planning Agent",
    "status": "idle"
}

# --------- Utilities ---------
def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def truncate(text, limit=260):
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "...(truncated)"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            memory = json.load(f)
    else:
        memory = {}

    memory.setdefault("completed_tasks", [])
    memory.setdefault("work_log", [])
    memory.setdefault("content_library", [])  # stores finished assets

    return memory

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def log_event(memory, event):
    memory["work_log"].append(event)
    save_memory(memory)

def print_memory_report(memory, last_n=10):
    print("\nRUN REPORT")
    print("=" * 50)
    total = len(memory["work_log"])
    completed = sum(1 for e in memory["work_log"] if e.get("status") == "completed")
    clarify = sum(1 for e in memory["work_log"] if e.get("status") == "clarify")
    skipped = sum(1 for e in memory["work_log"] if e.get("status") == "skipped")

    print(f"Total log entries: {total}")
    print(f"Completed: {completed} | Clarify: {clarify} | Skipped: {skipped}")
    print("\nLast 10 actions:")
    print("-" * 50)

    for entry in memory["work_log"][-last_n:]:
        print(f"{entry.get('timestamp')} | {entry.get('status')} | {entry.get('task')} | {entry.get('tool', '')}")
    print("-" * 50)

# --------- Tools (offline) ---------
def tool_generate_topics(goal, audience, tone):
    # simple "mock AI" topic generator
    return [
        f"{goal}: 3 mistakes to avoid",
        f"{goal}: the step-by-step beginner roadmap",
        f"{goal}: what I wish I knew earlier",
        f"{goal}: tools and resources I actually use",
        f"{goal}: quick wins you can do this week"
    ]

def tool_draft_post(topic, audience, tone, cta):
    # simple "mock AI" post writer
    return (
        f"Hook: {topic}\n\n"
        f"For {audience}:\n"
        f"- Key point 1: Keep it simple and consistent.\n"
        f"- Key point 2: Focus on one clear takeaway.\n"
        f"- Key point 3: Take one action today.\n\n"
        f"Tone: {tone}\n"
        f"CTA: {cta}\n"
    )

def tool_hashtags(niche):
    base = ["#contentstrategy", "#creator", "#marketing", "#smallbusiness", "#consistency"]
    if "ai" in niche.lower():
        base += ["#ai", "#aiautomation", "#aigent", "#promptengineering", "#futureofwork"]
    if "real estate" in niche.lower():
        base += ["#realestate", "#realtor", "#houstonrealestate", "#investing", "#homebuyers"]
    return base[:12]

def tool_schedule(topics):
    # 5-post weekly schedule (Mon-Fri)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    schedule = []
    for i, day in enumerate(days):
        topic = topics[i] if i < len(topics) else "Bonus: behind the scenes"
        schedule.append({"day": day, "topic": topic})
    return schedule

def tool_clarify(question):
    return f"I need one detail: {question}"

tools = {
    "generate_topics": tool_generate_topics,
    "draft_post": tool_draft_post,
    "hashtags": tool_hashtags,
    "schedule": tool_schedule,
    "clarify": tool_clarify
}

# --------- Workflow definition ---------
workflow = [
    {"id": "topics", "tool": "generate_topics"},
    {"id": "post_1", "tool": "draft_post"},
    {"id": "post_2", "tool": "draft_post"},
    {"id": "post_3", "tool": "draft_post"},
    {"id": "hashtags", "tool": "hashtags"},
    {"id": "schedule", "tool": "schedule"}
]

# --------- Decision + guardrails ---------
def should_skip(task_id, memory, run_key):
    # Prevent repeating the same workflow run
    completed_key = f"{run_key}:{task_id}"
    return completed_key in memory["completed_tasks"]

def mark_done(task_id, memory, run_key):
    memory["completed_tasks"].append(f"{run_key}:{task_id}")
    save_memory(memory)

def run_system(content_goal, audience, niche, tone, cta):
    agent["status"] = "working"
    memory = load_memory()

    # Run key helps you repeat workflows without collisions
    run_key = f"run:{content_goal.lower().strip()}"

    print(f"Agent {agent['name']} is online.\n")
    print(f"Goal: {content_goal}")
    print(f"Audience: {audience}")
    print(f"Niche: {niche}")
    print(f"Tone: {tone}")
    print(f"CTA: {cta}\n")
    print("-" * 50)

    # Guardrail: require a goal
    if not content_goal.strip():
        result = tools["clarify"]("What is the content goal?")
        log_event(memory, {
            "timestamp": now_iso(),
            "task": "clarify_goal",
            "tool": "clarify",
            "status": "clarify",
            "output": truncate(result)
        })
        print(result)
        print_memory_report(memory, last_n=10)
        return

    # Store outputs during the run (short-term memory)
    outputs = {}

    for step in workflow:
        task_id = step["id"]
        tool_name = step["tool"]

        if should_skip(task_id, memory, run_key):
            log_event(memory, {
                "timestamp": now_iso(),
                "task": task_id,
                "tool": tool_name,
                "status": "skipped",
                "reason": "Already completed for this goal"
            })
            continue

        # Build arguments based on tool
        if tool_name == "generate_topics":
            args = {"goal": content_goal, "audience": audience, "tone": tone}

        elif tool_name == "draft_post":
            # Choose topic from generated topics
            if "topics" not in outputs:
                result = tools["clarify"]("I need topics first. Run generate_topics.")
                log_event(memory, {
                    "timestamp": now_iso(),
                    "task": task_id,
                    "tool": "clarify",
                    "status": "clarify",
                    "output": truncate(result)
                })
                print(result)
                continue

            topic_index = {"post_1": 0, "post_2": 1, "post_3": 2}.get(task_id, 0)
            topic = outputs["topics"][topic_index]
            args = {"topic": topic, "audience": audience, "tone": tone, "cta": cta}

        elif tool_name == "hashtags":
            args = {"niche": niche}

        elif tool_name == "schedule":
            if "topics" not in outputs:
                result = tools["clarify"]("I need topics first to build a schedule.")
                log_event(memory, {
                    "timestamp": now_iso(),
                    "task": task_id,
                    "tool": "clarify",
                    "status": "clarify",
                    "output": truncate(result)
                })
                print(result)
                continue
            args = {"topics": outputs["topics"]}

        else:
            args = {}

        # Execute tool
        result = tools[tool_name](**args)

        # Save output into short-term memory
        outputs[task_id] = result

        # Persist assets into long-term memory content library
        memory["content_library"].append({
            "timestamp": now_iso(),
            "goal": content_goal,
            "asset_type": task_id,
            "tool": tool_name,
            "data": result
        })

        log_event(memory, {
            "timestamp": now_iso(),
            "task": task_id,
            "tool": tool_name,
            "args": args,
            "status": "completed",
            "output": truncate(result)
        })

        mark_done(task_id, memory, run_key)

    # Final output summary
    print("\nDELIVERABLES")
    print("=" * 50)

    topics = outputs.get("topics", [])
    if topics:
        print("\nTopics:")
        for t in topics:
            print("-", t)

    for pid in ["post_1", "post_2", "post_3"]:
        if pid in outputs:
            print(f"\n{pid.upper()}:\n{outputs[pid]}")

    if "hashtags" in outputs:
        print("\nHashtags:")
        print(" ".join(outputs["hashtags"]))

    if "schedule" in outputs:
        print("\nWeekly Schedule:")
        for item in outputs["schedule"]:
            print(f"{item['day']}: {item['topic']}")

    print_memory_report(memory, last_n=10)
    agent["status"] = "complete"
    print("\nAgent run complete.")

# --------- Run it ---------
if __name__ == "__main__":
    # Edit these inputs to match your brand
    content_goal = content_goal = "Build trust by documenting my journey learning AI agents from zero"
    audience = "busy entrepreneurs who want to level up"
    niche = "AI"
    tone = "direct, practical, supportive"
    cta = "Comment 'PLAN' and I will share the next steps."

    run_system(content_goal, audience, niche, tone, cta)

def get_local_socratic_fallback(
    target_q, student_message, active_concept_node, active_chapter, active_subject
):
    msg_lower = student_message.lower()
    header = "⚠️ [System Notice: Gemini API rate limit reached. Running local Socratic backup mode]\n\n"

    if msg_lower.startswith("please help me solve this question") and target_q:
        q_text = target_q.get("raw_text", "")
        snippet = q_text[:200] + "..." if len(q_text) > 200 else q_text

        return (
            header
            + f"**Option A - Let me break this down step by step:**\n"
            f"Let's look at this **{active_subject}** problem under the concept of **{active_chapter}**.\n"
            f"Question:\n> {snippet}\n\n"
            f"To get started, what are the primary variables or physical quantities given in the question, and what are we trying to calculate?\n\n"
            f"**Option B - Build your intuition with practice questions:**\n"
            f"Here are three adaptive practice questions for **{active_concept_node}**:\n"
            f"1. **Easy**: A basic conceptual question testing the definition and core units.\n"
            f"2. **Medium**: A standard problem with numerical application similar to the active question.\n"
            f"3. **Hard**: An advanced question combining multiple concepts from {active_chapter}.\n\n"
            f"Reply A to work through this problem together, or B to start with practice questions."
        )

    if msg_lower == "a":
        return (
            header
            + "Excellent! Let's work through the active question step by step.\n\n"
            "Step 1: Based on the question context, what is the formula or physical law that relates these quantities? (For example, Ohm's law, Faraday's law, or equations of motion?)\n\n"
            "Give it a try and type your formula or thoughts!"
        )

    if msg_lower == "b":
        return (
            header
            + "Awesome, let's build your intuition with practice questions first!\n\n"
            f"Let's start with the **Easy** foundational question:\n"
            f"> What is the fundamental unit of measurement/relation for {active_concept_node}?\n\n"
            "Type your answer, and I'll confirm if it's correct!"
        )

    return (
        header
        + "Thank you for your response! Let's examine that approach. \n\n"
        f"In the context of **{active_concept_node}**, how does that relate to the target question variables? Let's check our steps or formulas together. If you'd like to return to the options, type 'A' or 'B'!"
    )

from json_retrieval.prompts.prompts import STANDARD_SYSTEM_PROMPT, PERSONA_SYSTEM_PROMPT, QUERY_PROMPT, QUERY_PROMPT_WITH_CHUNKS

def generate_prompts(query, persona= None, chunks=None)->list[str,str]:
    if persona is None:
        system_prompt = STANDARD_SYSTEM_PROMPT
    else:
        system_prompt = PERSONA_SYSTEM_PROMPT.format(persona=persona)

    if chunks is None:
        query_prompt = QUERY_PROMPT.format(query=query)
    else:
        query_prompt = QUERY_PROMPT_WITH_CHUNKS.format(query=query,chunks=chunks)

    return [system_prompt,query_prompt]


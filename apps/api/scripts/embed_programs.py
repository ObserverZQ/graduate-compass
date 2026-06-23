# Selects all programs where embedding is null
# For each, constructs an embedding input string like:

#    {name} at {university}. Department: {department}. 
#    Research areas: {research_areas}. Description: {description}.

# Calls an embedding model (DeepSeek doesn't have a great one — use OpenAI's text-embedding-3-small at 1536 dims, ~$0.02 per million tokens, cheap)
# Updates the row
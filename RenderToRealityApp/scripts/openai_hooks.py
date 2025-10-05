import openai

MODEL = "gpt-4o-mini"

def init(api_key: str, model: str = "gpt-4o-mini"):
    global MODEL
    openai.api_key = api_key
    MODEL = model or MODEL

def ask(prompt: str, tone="technical", temperature=0.5):
    full_prompt = f"Write in a {tone} style.\n\n{prompt}"
    # Using legacy ChatCompletion style to match many environments
    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are an experienced project manager and AI automation assistant."},
            {"role": "user", "content": full_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()

def gen_status(project: str, completed, upcoming, risks, tone="technical"):
    prompt = f"""
Please draft a professional project status update for '{project}'.
Completed: {completed}
Upcoming: {upcoming}
Risks/Mitigations: {risks}
Keep it concise and actionable.
"""
    return ask(prompt, tone=tone)

def gen_risk_analysis(dataset_summary: str, tone="technical"):
    prompt = f"""
Analyze this project dataset:
{dataset_summary}

Identify key schedule or resource risks, mitigation strategies, and assign suggested responsible roles.
"""
    return ask(prompt, tone=tone)

def summarize_mesh_report(mesh_summary: dict, tone="technical"):
    prompt = f"""
Write a {tone} bullet-point summary of the new mesh build:

Project: {mesh_summary.get('project')}
Filename: {mesh_summary.get('filename')}
Dimensions (mm): W={mesh_summary.get('width_mm')}, D={mesh_summary.get('depth_mm')}, H={mesh_summary.get('height_mm')}
Volume: {mesh_summary.get('volume_cm3')} cm³
Triangles: {mesh_summary.get('triangles')}
Notes: {mesh_summary.get('notes')}
"""
    return ask(prompt, tone=tone)

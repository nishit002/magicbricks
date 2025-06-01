import streamlit as st
import requests
import pandas as pd
import re

# --- SECRETS FROM STREAMLIT CLOUD ---
PERPLEXITY_API_KEY = st.secrets["api"]["perplexity_key"]
GROK_API_KEY = st.secrets["api"]["grok_key"]

# --- PERPLEXITY CHAT COMPLETION ---
def call_perplexity_chat(locality, fields):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a precise and objective real estate researcher. Return factual insights as a numbered list, one item per requested field. Avoid vague responses like 'not found' or 'no data available'—only provide detailed, complete information."
            },
            {
                "role": "user",
                "content": f"Analyze {locality} based on: {', '.join(fields)}. Return a numbered list with one detailed paragraph per field. If data is unavailable for a field, skip that field and do not include it in the list."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return None, f"Perplexity API Error {response.status_code}: {response.text}"
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"].strip()
            return content, None
        return None, "Perplexity returned no usable content."
    except Exception as e:
        return None, f"Perplexity Exception: {str(e)}"

# --- GROK CHAT COMPLETION ---
def call_grok_chat(locality, fields):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-3-latest",
        "stream": False,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are a real estate analyst. Provide detailed, polished insights as a numbered list, one item per field. Avoid vague responses like 'not found' or 'no data available'—only include fields with complete, factual information."
            },
            {
                "role": "user",
                "content": f"Analyze {locality} based on: {', '.join(fields)}. Return a numbered list with one detailed paragraph per field. Do not include fields where data is unavailable or incomplete."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return None, f"Grok API Error {response.status_code}: {response.text}"
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"].strip()
            return content, None
        return None, "Grok returned no usable content."
    except Exception as e:
        return None, f"Grok Exception: {str(e)}"

# --- PARSE NUMBERED LIST OUTPUT ---
def parse_output_to_list(output, fields):
    if not output:
        return []
    # Split by numbered list entries (e.g., "0. ", "1. ", etc.)
    entries = []
    current_entry = ""
    lines = output.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Check if the line starts with a number followed by a dot (e.g., "0. ")
        if any(line.startswith(f"{i}. ") for i in range(len(fields))):
            if current_entry:
                entries.append(current_entry.strip())
            current_entry = line
        else:
            current_entry += " " + line
    if current_entry:
        entries.append(current_entry.strip())
    
    # Clean up entries by removing the numbering prefix and filtering incomplete data
    cleaned_entries = []
    for entry in entries:
        cleaned_entry = entry.split(". ", 1)[1] if ". " in entry else entry
        # Skip entries with "not found" or "no data available"
        if not re.search(r"(not found|no data available)", cleaned_entry, re.IGNORECASE):
            cleaned_entries.append(cleaned_entry)
    return cleaned_entries

# --- STREAMLIT UI ---
st.title("📍 AI-Powered Locality Research Tool")

locality_input = st.text_input("Enter a Locality or Project Name")

data_points = [
    "Real Estate Trends", "Connectivity", "Price Trends", "Nearby Infrastructure",
    "Rental Yield", "Demographics", "Growth Potential", "Public Transport", "Safety"
]

selected_fields = st.mult AscendingList = st.multiselect("Select Data Points to Fetch", options=data_points)

if st.button("🔍 Fetch Insights"):
    if not locality_input or not selected_fields:
        st.warning("Please enter a locality and select at least one data point.")
    else:
        with st.spinner("Contacting Perplexity and Grok APIs..."):
            # Try Perplexity first
            perplexity_output, perplexity_error = call_perplexity_chat(locality_input, selected_fields)
            fallback_used = False

            if perplexity_output is None:
                fallback_used = True
                grok_output, grok_error = call_grok_chat(locality_input, selected_fields)
                final_output = grok_output
                final_error = grok_error
            else:
                final_output = perplexity_output
                final_error = perplexity_error

        st.subheader("📊 Locality Research Results")
        if final_output:
            # Parse the output into a list of insights
            insights = parse_output_to_list(final_output, selected_fields)
            if not insights:
                st.warning("⚠️ No complete data available for the selected fields.")
            else:
                # Create a DataFrame for the table
                rows = []
                for i, field in enumerate(selected_fields):
                    if i < len(insights):
                        rows.append([field, insights[i]])
                
                df = pd.DataFrame(rows, columns=["Aspect", "Insights"])
                
                # Style the DataFrame for better presentation
                styled_df = df.style.set_properties(**{
                    'text-align': 'left',
                    'white-space': 'pre-wrap',
                    'border': '1px solid #ddd',
                    'padding': '8px',
                    'font-size': '14px'
                }).set_table_styles([
                    {'selector': 'th', 'props': [('background-color', '#f0f0f0'), ('font-weight', 'bold'), ('border', '1px solid #ddd'), ('padding', '8px')]}
                ])
                
                # Display the styled DataFrame
                st.dataframe(styled_df, use_container_width=True)
        else:
            st.warning("⚠️ No valid data received from either API.")

        if final_error:
            st.caption(f"🔧 Debug: {final_error}")
        elif fallback_used:
            st.caption("⚠️ Perplexity failed. Fallback used: Grok")

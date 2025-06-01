import streamlit as st
import requests
import pandas as pd

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
    prompt = (
        f"Provide a detailed factual analysis for {locality} based on the following aspects: {', '.join(fields)}. "
        f"For each aspect, include concrete numbers, such as average price per square foot, growth rates, rental yields, "
        f"and any available numerical data. Return exactly {len(fields)} paragraphs, one for each aspect, separated by double newlines."
    )
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a precise and objective real estate researcher. Return factual, data-driven paragraph summaries."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return None, f"Perplexity API Error {response.status_code}: {response.text}"
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return content.strip(), None
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
    prompt = (
        f"Provide detailed factual insights about {locality} based on the following aspects: {', '.join(fields)}. "
        f"For each aspect, include specific numbers such as average prices, rental yields, growth rates, and other relevant data. "
        f"Return exactly {len(fields)} paragraphs, one for each aspect in the order given, separated by double newlines."
    )
    payload = {
        "model": "grok-3-latest",
        "stream": False,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are a real estate analyst. Provide clean, data-driven paragraph summaries only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return None, f"Grok API Error {response.status_code}: {response.text}"
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return content.strip(), None
        return None, "Grok returned no usable content."
    except Exception as e:
        return None, f"Grok Exception: {str(e)}"

# --- STREAMLIT UI ---
st.title("📍 AI-Powered Locality Research Tool")

locality_input = st.text_input("Enter a Locality or Project Name")

data_points = [
    "Real Estate Trends", "Connectivity", "Price Trends", "Nearby Infrastructure",
    "Rental Yield", "Demographics", "Growth Potential", "Public Transport", "Safety"
]

selected_fields = st.multiselect("Select Data Points to Fetch", options=data_points)

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
                final_error = None

        st.subheader("📊 Locality Research Results")
        if final_output:
            # Split by double newlines to separate paragraphs
            paragraphs = [p.strip() for p in final_output.split("\n\n") if p.strip()]
            
            # Check if the number of paragraphs matches the number of selected fields
            if len(paragraphs) != len(selected_fields):
                st.warning(
                    f"⚠️ Expected {len(selected_fields)} paragraphs but received {len(paragraphs)}. "
                    "Please try again or select different data points."
                )
            else:
                # Create rows by pairing each field with its corresponding paragraph
                rows = [[i + 1, selected_fields[i], paragraphs[i]] for i in range(len(selected_fields))]
                df = pd.DataFrame(rows, columns=["#", "Aspect", "Insights"])

                # Enhance table display
                st.markdown("""
                    <style>
                        .streamlit-expanderHeader {
                            font-size: 1.2em;
                        }
                        table {
                            width: 100%;
                            border-collapse: collapse;
                        }
                        table, th, td {
                            border: 1px solid #ddd;
                        }
                        th, td {
                            padding: 10px;
                            text-align: left;
                        }
                        th {
                            background-color: #f2f2f2;
                        }
                        tr:nth-child(even) {
                            background-color: #f9f9f9;
                        }
                    </style>
                """, unsafe_allow_html=True)
                st.dataframe(df.style.set_properties(**{
                    "font-size": "14px",
                    "color": "black",
                    "background-color": "#f9f9f9",
                    "border-color": "#ddd"
                }))
        else:
            st.warning("⚠️ No valid data received from either API.")

        if final_error:
            st.caption(f"🔧 Debug: {final_error}")
        elif fallback_used:
            st.caption("⚠️ Perplexity failed. Fallback used: Grok")

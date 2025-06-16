from dataforseo_client import DataForSeoClient
import asyncio
import platform

# Initialize DataForSEO Client with your API credentials
client = DataForSeoClient('your_username', 'your_password')

# Magicbricks domain and competitor domains
magicbricks_domain = "magicbricks.com"
competitors = ["99acres.com", "housing.com"]

async def fetch_existing_topics():
    # Placeholder for scraping Magicbricks blog (replace with actual scraper logic)
    # For now, simulate with a sample list based on the MahaRERA article
    return ["maharera 2025", "maharera registration", "maharera complaints"]

async def get_keyword_gaps():
    task_post_data = []
    for competitor in competitors:
        task_post_data.append({
            "target1": magicbricks_domain,
            "target2": competitor,
            "language_code": "en",
            "location_code": 2840,  # United States as default, adjust to India (e.g., 299)
            "intersections": "false",
            "limit": 1000
        })

    # Send request to DataForSeo Domain Intersection API
    response = await client.labs.domain_intersection.post(task_post_data)
    keyword_gaps = []

    if response and 'tasks' in response:
        for task in response['tasks']:
            if 'result' in task:
                for result in task['result']:
                    keyword = result.get('keyword', '').lower()
                    search_volume = result.get('keyword_info', {}).get('search_volume', 0)
                    if search_volume > 1000:  # Filter for significant search volume
                        keyword_gaps.append(keyword)

    return keyword_gaps

async def generate_new_topics(existing_topics, keyword_gaps):
    new_topics = []
    existing_set = set(existing_topics)
    
    for gap in keyword_gaps:
        if gap not in existing_set and any(word in gap for word in ["real estate", "property", "maharera", "housing"]):
            # Refine gaps into article-friendly topics
            topic = gap.replace("-", " ").title()
            if "maharera" in gap:
                topic = f"How to Navigate {topic} for Homebuyers"
            elif "real estate" in gap:
                topic = f"2025 {topic} Trends in India"
            new_topics.append(topic)

    return new_topics[:10]  # Limit to top 10 ideas

async def main():
    # Fetch existing topics from Magicbricks
    existing_topics = await fetch_existing_topics()
    
    # Get keyword gaps from DataForSEO
    keyword_gaps = await get_keyword_gaps()
    
    # Generate new topics
    new_topics = await generate_new_topics(existing_topics, keyword_gaps)
    
    # Output results
    for topic in new_topics:
        print(f"- {topic}")

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())

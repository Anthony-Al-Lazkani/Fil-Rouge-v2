from pyalex import Works, config

# Add email to configuration for faster responses (recommended on the official open alex documentation
config.email = "anthonylazkani.22@gmail.com"

# Query
# Example: Fetch 5 articles about "Carbon Capture" published after 2022
results = (
    Works()
    .search("artificial intelligence")
    .filter(from_publication_date="2020")
    .get(per_page=5)
)

# 3. Print results
for work in results:
    print(f"Title: {work['title']}")
    print(f"DOI: {work['doi']}")
    print(f"Cited by: {work['cited_by_count']}")
    print("-" * 20)
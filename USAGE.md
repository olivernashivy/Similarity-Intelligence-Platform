# Usage Guide

## Quick Start

### Using the API

1. **Start the service**:
   ```bash
   docker-compose up -d
   ```

2. **Analyze an article**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/similarity/analyze" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Understanding Machine Learning",
       "content": "Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. It involves algorithms that can identify patterns and make decisions based on input data."
     }'
   ```

3. **Check health**:
   ```bash
   curl http://localhost:8000/health
   ```

## Examples

### Example 1: Technology Article

**Input**:
```json
{
  "title": "The Rise of Quantum Computing",
  "content": "Quantum computing represents a paradigm shift in computational power. Unlike classical computers that use bits, quantum computers use quantum bits or qubits. These qubits can exist in multiple states simultaneously due to superposition, enabling quantum computers to solve complex problems exponentially faster than classical computers."
}
```

**Expected Output**:
- Videos about quantum computing fundamentals
- Explanations of qubits and superposition
- Quantum vs classical computing comparisons

### Example 2: Tutorial Content

**Input**:
```json
{
  "title": "Python Flask Tutorial for Beginners",
  "content": "Flask is a micro web framework written in Python. It is designed to make getting started quick and easy, with the ability to scale up to complex applications. This tutorial covers creating routes, rendering templates, and handling form data in Flask applications."
}
```

**Expected Output**:
- Flask tutorial videos
- Python web development guides
- Specific Flask concepts (routes, templates)

### Example 3: News Article

**Input**:
```json
{
  "title": "SpaceX Successfully Launches Starship",
  "content": "SpaceX achieved a major milestone today with the successful launch and landing of its Starship spacecraft. The fully reusable launch system represents a significant step toward making space travel more accessible and affordable. The mission demonstrated advanced orbital mechanics and precision landing capabilities."
}
```

**Expected Output**:
- SpaceX Starship launch coverage
- Space technology explanations
- Orbital mechanics videos

## Understanding Results

### Similarity Scores

The system returns similarity scores ranging from 0 to 1:

- **0.80 - 0.85**: Moderate similarity - Some conceptual overlap
- **0.85 - 0.90**: High similarity - Significant content similarity
- **0.90 - 0.95**: Very high similarity - Strong semantic match
- **0.95 - 1.00**: Extremely high similarity - Nearly identical content

### Interpreting Matches

Each match includes:

1. **Video Metadata**:
   - Title, channel, URL
   - Total duration
   - Upload date (future feature)

2. **Match Details**:
   - Timestamp range (e.g., "02:15 - 03:45")
   - Similarity score
   - Number of matched chunks
   - Coverage percentage

3. **Transcript Snippet**:
   - Up to 300 characters
   - Shows matched content
   - Helps verify relevance

### Coverage Percentage

Indicates how much of the video matches the article:

- **< 5%**: Very specific match in a longer video
- **5% - 15%**: Moderate coverage, specific section
- **15% - 30%**: Substantial coverage
- **> 30%**: Majority of video relates to article

## API Integration

### Python Example

```python
import requests

def analyze_article(title: str, content: str):
    url = "http://localhost:8000/api/v1/similarity/analyze"

    payload = {
        "title": title,
        "content": content
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        results = response.json()
        print(f"Found {results['matches_found']} matches")

        for video_result in results['results']:
            print(f"\nVideo: {video_result['video_title']}")
            print(f"Channel: {video_result['channel_name']}")
            print(f"Max Similarity: {video_result['max_similarity']:.2f}")
            print(f"URL: {video_result['video_url']}")

            for match in video_result['matches']:
                print(f"  - {match['timestamp_range']}: {match['similarity_score']:.2f}")
    else:
        print(f"Error: {response.status_code}")

# Example usage
analyze_article(
    title="Understanding Neural Networks",
    content="Neural networks are computational models inspired by biological neural networks..."
)
```

### JavaScript Example

```javascript
async function analyzeArticle(title, content) {
  const url = 'http://localhost:8000/api/v1/similarity/analyze';

  const payload = {
    title: title,
    content: content
  };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      const results = await response.json();
      console.log(`Found ${results.matches_found} matches`);

      results.results.forEach(videoResult => {
        console.log(`\nVideo: ${videoResult.video_title}`);
        console.log(`Channel: ${videoResult.channel_name}`);
        console.log(`Max Similarity: ${videoResult.max_similarity.toFixed(2)}`);
        console.log(`URL: ${videoResult.video_url}`);

        videoResult.matches.forEach(match => {
          console.log(`  - ${match.timestamp_range}: ${match.similarity_score.toFixed(2)}`);
        });
      });
    } else {
      console.error(`Error: ${response.status}`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// Example usage
analyzeArticle(
  'Understanding Neural Networks',
  'Neural networks are computational models inspired by biological neural networks...'
);
```

## Best Practices

### Article Content

1. **Minimum Length**: At least 200 words for meaningful analysis
2. **Clear Topics**: Well-defined subject matter works best
3. **Technical Content**: More specific content yields better matches
4. **Language**: English only for current version

### Optimization Tips

1. **Use Caching**: Let the system cache results for 24 hours
2. **Monitor Quotas**: Track YouTube API and OpenAI API usage
3. **Adjust Thresholds**: Lower threshold (0.75) for more matches
4. **Limit Videos**: Start with 5-10 videos, increase if needed

### Common Patterns

**Good for**:
- Educational content
- Technical tutorials
- News articles with specific topics
- How-to guides
- Product reviews with details

**Less effective for**:
- Very short articles (< 200 words)
- Highly generic content
- Poetry or creative writing
- Lists without explanations
- Entertainment-focused content

## Monitoring

### Cache Statistics

```bash
curl http://localhost:8000/api/v1/similarity/cache/stats
```

Returns:
```json
{
  "enabled": true,
  "connected": true,
  "total_keys": 45,
  "used_memory": "2.5M",
  "ttl_hours": 24
}
```

### Clear Cache

```bash
curl -X DELETE http://localhost:8000/api/v1/similarity/cache/clear
```

## Troubleshooting

### No Matches Found

1. **Check keywords**: Review `keywords_extracted` in response
2. **Broaden search**: Lower similarity threshold
3. **Increase videos**: Raise `MAX_VIDEOS_PER_CHECK`
4. **Verify topic**: Ensure topic has YouTube content

### Rate Limiting

1. **YouTube API**: 10,000 units/day default
   - Each search uses ~100 units
   - Each video detail uses ~1 unit
2. **OpenAI API**: Depends on tier
   - Monitor token usage
   - Use caching effectively

### Performance Issues

1. **Slow responses**: Enable caching
2. **API timeouts**: Reduce max videos
3. **Memory usage**: Lower chunk size
4. **High costs**: Adjust video duration limit

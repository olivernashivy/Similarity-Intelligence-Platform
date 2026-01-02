#!/usr/bin/env python3
"""Seed sample articles for testing similarity detection."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.embeddings import get_embedding_generator
from app.core.vector_store import get_article_store, VectorMetadata
from app.core.chunking import TextChunker


# Sample articles covering different topics
SAMPLE_ARTICLES = [
    {
        "title": "Introduction to Machine Learning",
        "url": "https://example.com/ml-intro",
        "text": """
        Machine learning is a subset of artificial intelligence that focuses on building systems
        that can learn from and make decisions based on data. Unlike traditional programming where
        explicit instructions are given, machine learning algorithms discover patterns in data and
        use those patterns to make predictions or decisions.

        There are three main types of machine learning: supervised learning, unsupervised learning,
        and reinforcement learning. Supervised learning uses labeled training data to learn the
        relationship between inputs and outputs. Unsupervised learning finds hidden patterns in
        unlabeled data. Reinforcement learning learns through trial and error by receiving rewards
        or penalties.

        Common applications of machine learning include image recognition, natural language processing,
        recommendation systems, fraud detection, and autonomous vehicles. The field has grown rapidly
        due to increases in computing power, availability of large datasets, and advances in algorithms
        like deep learning neural networks.
        """
    },
    {
        "title": "Deep Learning and Neural Networks",
        "url": "https://example.com/deep-learning",
        "text": """
        Deep learning is a specialized branch of machine learning that uses artificial neural networks
        with multiple layers to progressively extract higher-level features from raw input. These
        neural networks are inspired by the structure and function of the human brain, with
        interconnected nodes that process and transform information.

        Convolutional Neural Networks (CNNs) are particularly effective for image processing and
        computer vision tasks. They use specialized layers that can detect features like edges,
        textures, and patterns in visual data. Recurrent Neural Networks (RNNs) and their variants
        like LSTMs are designed for sequential data and are widely used in natural language processing.

        Transformer architectures have revolutionized NLP since their introduction in 2017. Models
        like BERT, GPT, and T5 use attention mechanisms to process text more effectively than
        traditional RNNs. These models have achieved state-of-the-art results on tasks like
        translation, summarization, and question answering.
        """
    },
    {
        "title": "Natural Language Processing Fundamentals",
        "url": "https://example.com/nlp-fundamentals",
        "text": """
        Natural Language Processing (NLP) is the field of artificial intelligence concerned with
        enabling computers to understand, interpret, and generate human language. NLP combines
        computational linguistics with machine learning and deep learning to process text and speech.

        Key NLP tasks include tokenization, part-of-speech tagging, named entity recognition,
        sentiment analysis, machine translation, and text summarization. Modern NLP systems use
        word embeddings to represent words as dense vectors that capture semantic relationships
        between words based on their context.

        Pre-trained language models have transformed NLP by learning general language understanding
        from massive text corpora. These models can be fine-tuned for specific tasks with relatively
        small amounts of task-specific data. This transfer learning approach has made advanced NLP
        capabilities accessible to more applications and organizations.
        """
    },
    {
        "title": "Cloud Computing and Scalability",
        "url": "https://example.com/cloud-computing",
        "text": """
        Cloud computing provides on-demand access to computing resources over the internet, including
        servers, storage, databases, networking, and software. The three main service models are
        Infrastructure as a Service (IaaS), Platform as a Service (PaaS), and Software as a Service (SaaS).

        Major cloud providers like AWS, Azure, and Google Cloud offer a wide range of services that
        enable businesses to scale applications without managing physical infrastructure. Auto-scaling
        allows applications to automatically adjust resources based on demand, improving both
        performance and cost efficiency.

        Containerization with Docker and orchestration with Kubernetes have become standard practices
        for deploying cloud applications. These technologies provide consistency across environments,
        efficient resource utilization, and simplified deployment processes. Microservices architecture
        complements these tools by breaking applications into smaller, independently deployable services.
        """
    },
    {
        "title": "Cybersecurity Best Practices",
        "url": "https://example.com/cybersecurity",
        "text": """
        Cybersecurity is the practice of protecting systems, networks, and data from digital attacks
        and unauthorized access. As our reliance on technology grows, so does the importance of
        implementing robust security measures across all aspects of IT infrastructure.

        Key security principles include defense in depth, least privilege access, and zero trust
        architecture. Defense in depth uses multiple layers of security controls to protect assets.
        Least privilege means giving users only the minimum access needed to perform their jobs.
        Zero trust assumes no user or system should be trusted by default, even inside the network perimeter.

        Common security measures include encryption for data at rest and in transit, multi-factor
        authentication, regular security audits and penetration testing, employee security awareness
        training, and incident response planning. Keeping software updated and patched is crucial
        for preventing exploitation of known vulnerabilities.
        """
    },
    {
        "title": "Agile Software Development Methodology",
        "url": "https://example.com/agile-methodology",
        "text": """
        Agile software development is an iterative approach that emphasizes flexibility, collaboration,
        and customer feedback. Instead of planning entire projects upfront, agile teams work in
        short cycles called sprints, typically lasting one to four weeks, delivering working software
        incrementally.

        The Agile Manifesto values individuals and interactions over processes and tools, working
        software over comprehensive documentation, customer collaboration over contract negotiation,
        and responding to change over following a plan. Popular agile frameworks include Scrum,
        Kanban, and Extreme Programming (XP).

        Scrum uses defined roles like Product Owner, Scrum Master, and Development Team, along with
        ceremonies like sprint planning, daily standups, sprint reviews, and retrospectives. Kanban
        focuses on visualizing work, limiting work in progress, and optimizing flow. Both frameworks
        promote continuous improvement and adaptive planning based on actual progress and feedback.
        """
    },
    {
        "title": "Database Design and Optimization",
        "url": "https://example.com/database-design",
        "text": """
        Database design is the process of organizing data into tables and defining relationships
        between them to support efficient data storage and retrieval. Good database design follows
        normalization principles to reduce data redundancy and improve data integrity.

        Relational databases like PostgreSQL and MySQL use SQL for querying and are ideal for
        structured data with complex relationships. NoSQL databases like MongoDB and Cassandra
        are designed for unstructured or semi-structured data and offer flexible schemas and
        horizontal scalability.

        Database optimization involves creating appropriate indexes, writing efficient queries,
        partitioning large tables, and implementing caching strategies. Query optimization includes
        analyzing execution plans, avoiding N+1 queries, using joins efficiently, and selecting
        only needed columns. Connection pooling and read replicas can improve performance for
        high-traffic applications.
        """
    },
    {
        "title": "DevOps Culture and Practices",
        "url": "https://example.com/devops-culture",
        "text": """
        DevOps is a cultural and technical movement that emphasizes collaboration between development
        and operations teams to deliver software faster and more reliably. It combines practices,
        tools, and cultural philosophies that automate and integrate software development and IT operations.

        Core DevOps practices include continuous integration (CI), continuous delivery (CD),
        infrastructure as code (IaC), monitoring and logging, and automated testing. CI/CD pipelines
        automatically build, test, and deploy code changes, reducing manual errors and accelerating
        release cycles.

        Infrastructure as code uses tools like Terraform and Ansible to define and provision
        infrastructure through code rather than manual processes. This approach ensures consistency
        across environments, enables version control of infrastructure, and allows for automated
        infrastructure changes. Monitoring tools provide visibility into application performance
        and help teams quickly identify and resolve issues.
        """
    },
    {
        "title": "Blockchain Technology Explained",
        "url": "https://example.com/blockchain-tech",
        "text": """
        Blockchain is a distributed ledger technology that maintains a continuously growing list
        of records called blocks, linked together using cryptography. Each block contains a
        cryptographic hash of the previous block, a timestamp, and transaction data, making the
        chain tamper-resistant.

        The decentralized nature of blockchain means no single entity controls the entire network.
        Consensus mechanisms like Proof of Work (used by Bitcoin) or Proof of Stake (used by
        Ethereum 2.0) ensure agreement on the state of the ledger without requiring a central authority.

        Beyond cryptocurrencies, blockchain has applications in supply chain management, digital
        identity verification, smart contracts, and voting systems. Smart contracts are self-executing
        contracts with terms directly written into code, automatically enforcing agreements without
        intermediaries. However, blockchain faces challenges including scalability limitations,
        energy consumption, and regulatory uncertainty.
        """
    },
    {
        "title": "API Design and RESTful Architecture",
        "url": "https://example.com/api-design",
        "text": """
        Application Programming Interfaces (APIs) enable different software applications to communicate
        with each other. RESTful APIs follow REST (Representational State Transfer) architectural
        principles, using HTTP methods like GET, POST, PUT, and DELETE to perform operations on resources.

        Good API design includes using clear and consistent naming conventions, proper HTTP status
        codes, versioning strategies, and comprehensive documentation. APIs should be stateless,
        meaning each request contains all information needed to process it, without relying on
        stored context on the server.

        API security is crucial and involves authentication mechanisms like API keys, OAuth 2.0,
        or JWT tokens, rate limiting to prevent abuse, input validation, and encryption for data
        in transit. GraphQL is an alternative to REST that allows clients to request exactly the
        data they need, reducing over-fetching and under-fetching issues common with REST endpoints.
        """
    }
]


async def seed_articles():
    """Seed sample articles into the vector store."""
    print("=" * 80)
    print("Seeding Sample Articles for Similarity Detection")
    print("=" * 80)
    print()

    # Initialize components
    print("Initializing components...")
    embedder = get_embedding_generator()
    chunker = TextChunker(min_words=40, max_words=60, overlap_words=10)
    article_store = get_article_store()

    # Check if store already has data
    existing_count = article_store.count()
    if existing_count > 0:
        print(f"⚠️  Warning: Article store already contains {existing_count} vectors")
        response = input("Do you want to continue and add more articles? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    print(f"Processing {len(SAMPLE_ARTICLES)} sample articles...")
    print()

    total_chunks = 0

    for idx, article in enumerate(SAMPLE_ARTICLES, 1):
        print(f"[{idx}/{len(SAMPLE_ARTICLES)}] Processing: {article['title']}")

        # Chunk the article
        chunks = chunker.chunk_text(article['text'], normalize=True)
        print(f"   Created {len(chunks)} chunks")

        # Generate embeddings
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedder.encode(chunk_texts, normalize=True)
        print(f"   Generated embeddings ({embeddings.shape})")

        # Create metadata
        metadata_list = [
            VectorMetadata(
                source_id=article['url'],
                source_type="article",
                chunk_index=i,
                chunk_text=chunk.text,
                title=article['title'],
                identifier=article['url']
            )
            for i, chunk in enumerate(chunks)
        ]

        # Add to store
        article_store.add_vectors(embeddings, metadata_list)
        total_chunks += len(chunks)

        print(f"   ✓ Added to vector store")
        print()

    # Save the store
    print("Saving vector store to disk...")
    article_store.save()

    print()
    print("=" * 80)
    print("✅ Seeding Complete!")
    print("=" * 80)
    print(f"Total articles added: {len(SAMPLE_ARTICLES)}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Total vectors in store: {article_store.count()}")
    print()
    print("You can now run similarity checks against these articles!")
    print()
    print("Example:")
    print("  curl -X POST http://localhost:8000/v1/check \\")
    print("    -H 'X-API-Key: YOUR_API_KEY' \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{")
    print('      "article_text": "Machine learning uses neural networks to process data...",')
    print('      "sources": ["articles"]')
    print("    }'")
    print()


if __name__ == "__main__":
    asyncio.run(seed_articles())

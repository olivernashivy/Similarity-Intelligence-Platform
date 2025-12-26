"""Keyword extraction service for identifying relevant search terms from articles."""

import re
from typing import List, Set
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """
    Extracts keywords and keyphrases from article text for YouTube search.

    Uses multiple strategies:
    - Title-weighted terms (terms from title given higher weight)
    - Named entities (capitalized sequences, proper nouns)
    - High-frequency meaningful terms (TF-IDF approximation)
    """

    # Common stop words to exclude
    STOP_WORDS: Set[str] = {
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and',
        'any', 'are', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below',
        'between', 'both', 'but', 'by', 'can', 'cannot', 'could', 'did', 'do', 'does',
        'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had',
        'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him',
        'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself',
        'just', 'me', 'might', 'more', 'most', 'must', 'my', 'myself', 'no', 'nor',
        'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours',
        'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some',
        'such', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then',
        'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under',
        'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 'which',
        'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'you', 'your', 'yours',
        'yourself', 'yourselves'
    }

    def __init__(self, max_keywords: int = 15):
        """
        Initialize keyword extractor.

        Args:
            max_keywords: Maximum number of keywords to extract per category
        """
        self.max_keywords = max_keywords

    def extract_keywords(
        self,
        title: str,
        content: str
    ) -> dict:
        """
        Extract keywords from article title and content.

        Args:
            title: Article title
            content: Article content

        Returns:
            Dictionary with keyword categories
        """
        # Extract different types of keywords
        title_weighted = self._extract_title_weighted_terms(title, content)
        named_entities = self._extract_named_entities(content)
        tfidf_phrases = self._extract_high_frequency_terms(content)

        # Combine and deduplicate
        all_keywords = list(set(title_weighted + named_entities + tfidf_phrases))

        logger.info(f"Extracted {len(all_keywords)} unique keywords from article")

        return {
            "title_weighted_terms": title_weighted[:self.max_keywords],
            "named_entities": named_entities[:self.max_keywords],
            "tfidf_phrases": tfidf_phrases[:self.max_keywords],
            "all_keywords": all_keywords[:self.max_keywords * 2]
        }

    def _extract_title_weighted_terms(self, title: str, content: str) -> List[str]:
        """
        Extract terms from title that also appear in content.

        Args:
            title: Article title
            content: Article content

        Returns:
            List of title-weighted terms
        """
        # Clean and tokenize title
        title_words = self._tokenize(title.lower())
        content_lower = content.lower()

        # Filter meaningful title words that appear in content
        weighted_terms = [
            word for word in title_words
            if len(word) > 3
            and word not in self.STOP_WORDS
            and word in content_lower
        ]

        # Also look for title phrases (2-3 words)
        title_phrases = self._extract_phrases(title, min_length=2, max_length=3)
        weighted_terms.extend([
            phrase for phrase in title_phrases
            if phrase.lower() in content_lower
        ])

        return weighted_terms

    def _extract_named_entities(self, text: str) -> List[str]:
        """
        Extract potential named entities (capitalized sequences).

        Args:
            text: Input text

        Returns:
            List of named entities
        """
        # Find capitalized words and sequences
        # Pattern: Words that start with capital letter
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        entities = re.findall(pattern, text)

        # Filter out common false positives
        entities = [
            entity for entity in entities
            if len(entity) > 2
            and entity.lower() not in self.STOP_WORDS
            and not entity.isupper()  # Exclude ALL CAPS
        ]

        # Count occurrences and return most frequent
        entity_counts = Counter(entities)
        return [entity for entity, _ in entity_counts.most_common(self.max_keywords)]

    def _extract_high_frequency_terms(self, text: str) -> List[str]:
        """
        Extract high-frequency meaningful terms (TF-IDF approximation).

        Args:
            text: Input text

        Returns:
            List of high-frequency terms
        """
        # Tokenize and clean
        words = self._tokenize(text.lower())

        # Filter meaningful words
        meaningful_words = [
            word for word in words
            if len(word) > 4
            and word not in self.STOP_WORDS
            and word.isalpha()
        ]

        # Count frequencies
        word_counts = Counter(meaningful_words)

        # Also extract multi-word phrases
        phrases = self._extract_phrases(text, min_length=2, max_length=3)
        phrase_counts = Counter(phrases)

        # Combine and rank
        combined = list(word_counts.most_common(self.max_keywords // 2))
        combined.extend(list(phrase_counts.most_common(self.max_keywords // 2)))

        return [term for term, _ in combined]

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of words
        """
        # Remove punctuation except hyphens in words
        text = re.sub(r'[^\w\s-]', ' ', text)
        return [word.strip() for word in text.split() if word.strip()]

    def _extract_phrases(
        self,
        text: str,
        min_length: int = 2,
        max_length: int = 3
    ) -> List[str]:
        """
        Extract multi-word phrases from text.

        Args:
            text: Input text
            min_length: Minimum phrase length in words
            max_length: Maximum phrase length in words

        Returns:
            List of phrases
        """
        words = self._tokenize(text)
        phrases = []

        for n in range(min_length, max_length + 1):
            for i in range(len(words) - n + 1):
                phrase_words = words[i:i + n]

                # Skip if contains stop words at boundaries
                if phrase_words[0].lower() in self.STOP_WORDS:
                    continue
                if phrase_words[-1].lower() in self.STOP_WORDS:
                    continue

                phrase = ' '.join(phrase_words)
                if len(phrase) > 6:  # Minimum phrase length in characters
                    phrases.append(phrase)

        return phrases

    def build_search_query(self, keywords: dict, max_terms: int = 5) -> str:
        """
        Build a YouTube search query from extracted keywords.

        Args:
            keywords: Dictionary of extracted keywords
            max_terms: Maximum number of terms to include in query

        Returns:
            Search query string
        """
        # Prioritize title-weighted terms and named entities
        query_terms = []

        # Add title-weighted terms (highest priority)
        query_terms.extend(keywords.get("title_weighted_terms", [])[:3])

        # Add named entities
        query_terms.extend(keywords.get("named_entities", [])[:2])

        # Fill remaining with TF-IDF terms if needed
        if len(query_terms) < max_terms:
            remaining = max_terms - len(query_terms)
            query_terms.extend(keywords.get("tfidf_phrases", [])[:remaining])

        # Deduplicate while preserving order
        seen = set()
        unique_terms = []
        for term in query_terms:
            term_lower = term.lower()
            if term_lower not in seen:
                seen.add(term_lower)
                unique_terms.append(term)

        return ' '.join(unique_terms[:max_terms])

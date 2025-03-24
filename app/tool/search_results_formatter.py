from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

class SearchResultsFormatter:
    '''Formats search results for better readability and clarity.'''

    @staticmethod
    def format_results(search_results: Union[List[Dict[str, str]], Dict[str, Any], str], query: str = "") -> str:
        '''Formats search results.'''
        logger.info("SearchResultsFormatter.format_results called")
        logger.info(f"Input Query: {query}")
        logger.info(f"Input search_results: {search_results}")
        logger.debug(f"Input search_results type: {type(search_results)}")
        if isinstance(search_results, dict):
            logger.debug(f"search_results keys: {search_results.keys()}")
        elif isinstance(search_results, list):
            logger.debug(f"search_results length: {len(search_results)}")
        logger.debug(f"search_results is string: {isinstance(search_results, str)}")
        logger.debug(f"search_results is dict: {isinstance(search_results, dict)}")
        logger.debug(f"search_results is list: {isinstance(search_results, list)}")

        if not search_results:
            logger.info("No search results provided.")  # Log when no results
            logger.info("No search results provided.") # Log when no results
            return "No relevant search results found."

        if isinstance(search_results, str):
            return search_results

        if isinstance(search_results, dict) and 'formatted_results' in search_results:
            formatted_text = search_results.get('formatted_results')
            if formatted_text:
                logger.info(f"Formatted output (from dict): {formatted_text}")
                return formatted_text

        if isinstance(search_results, dict) and 'results' in search_results:
            results = search_results.get('results', [])
        elif isinstance(search_results, list):
            results = search_results
        else:
            return "Unexpected search result format."

        if not results:
            return "No relevant search results found."

        formatted_lines = [f"Search results:\\n"]
        for i, result in enumerate(results, 1):
            title = SearchResultsFormatter._clean_text(result.get('title', 'N/A'))
            url = SearchResultsFormatter._clean_url(result.get('url', 'N/A'))
            snippet = SearchResultsFormatter._clean_text(result.get('snippet', 'N/A'))

            formatted_lines.append(f"{i}. {title}")
            formatted_lines.append(f"   URL: {url}")
            formatted_lines.append(f"   {snippet}\\n")

        output = "\\n".join(formatted_lines)
        logger.info(f"Formatted output: {output}")
        return output

    @staticmethod
    def _clean_text(text: str) -> str:
        '''Cleans up text.'''
        if not text:
            return "N/A"
        text = text.strip()
        text = ' '.join(text.split())
        return text

    @staticmethod
    def _clean_url(url: str) -> str:
        '''Cleans up URLs.'''
        if not url:
            return "N/A"
        return url.strip()

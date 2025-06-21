import os
from groundx import GroundX, BadRequestError
import logging
from pprint import pprint

logger = logging.getLogger(__name__)



class GroundService:
    def __init__(self, group_name="main_group", auto_load_buckets=True):
        try:
            self.api_key = os.getenv("GROUNDX_API_KEY")
            self.client = GroundX(api_key=self.api_key)
            self.target_group_name = group_name
            group = self.init_group()
            self._group_id = group.group_id

            if auto_load_buckets:
                self.load_buckets()

        except Exception as e:
            self.client = None
            logging.error(f"Failed to initialize groundx client: {str(e)}")
            raise e

    @property
    def group_id(self):
        """Get the cached group ID"""
        if self._group_id is None:
            # Fallback to fetching if not cached
            group = self.get_group_by_name(self.target_group_name)
            self._group_id = group.group_id if group else None
        return self._group_id

    @property
    def group(self):
        """Always fetch fresh group data"""
        return self.get_group_by_name(self.target_group_name)

    def init_group(self):
        try:
            group_names = self.list_group_names()

            # If group already exists, return it
            if group_names and self.target_group_name in group_names:
                # You'll need to implement get_group_by_name or similar
                existing_group = self.get_group_by_name(self.target_group_name)
                logger.info(f"Group '{self.target_group_name}' already exists")
                return existing_group

            # Create new group
            logger.info(f"Creating new group: {self.target_group_name}")
            group_response = self.create_group(group_name=self.target_group_name)

            if group_response is None:
                raise Exception(f"Failed to create group '{self.target_group_name}': create_group returned None")

            return group_response.group

        except Exception as e:
            # Log the full exception details
            logger.error(f"Failed to initialize group '{self.target_group_name}': {type(e).__name__}: {str(e)}")
            raise

    def load_buckets(self):
        """Load all system buckets into the target group"""
        try:
            # Get all buckets in the system
            all_buckets_response = self.client.buckets.list()
            if not all_buckets_response or not all_buckets_response.buckets:
                logger.info("No buckets found in system")
                return

            # Get current group with its buckets
            current_group = self.get_group_by_name(self.target_group_name)

            # Extract bucket IDs already in the group
            group_bucket_ids = []
            if current_group and hasattr(current_group, 'buckets') and current_group.buckets:
                group_bucket_ids = [b.bucket_id for b in current_group.buckets]

            # Add any system buckets not already in the group
            added_count = 0
            for bucket in all_buckets_response.buckets:
                if bucket.bucket_id not in group_bucket_ids:
                    try:
                        self.add_bucket_to_group(
                            group_name=self.target_group_name,
                            bucket_id=bucket.bucket_id
                        )
                        logger.info(f"Added bucket '{bucket.name}' (ID: {bucket.bucket_id}) to group")
                        added_count += 1
                    except Exception as e:
                        logger.error(f"Failed to add bucket {bucket.bucket_id}: {str(e)}")

            logger.info(f"Added {added_count} buckets to group '{self.target_group_name}'")

        except Exception as e:
            logger.error(f"Failed to load buckets into group: {str(e)}")
            raise


    def create_bucket(self, bucket_name):
        """
        Creates a bucket with the given name
        :param bucket_name:
        :return bucket_id:
        """
        if bucket_name is None:
            logger.info("No bucket name provided")
            return None
        try:
            response = self.client.buckets.create(name=bucket_name)
            logger.info(response)
            return response.bucket.bucket_id
        except Exception as e:
            logger.error(f"Failed to create bucket: {str(e)}")
            raise e

    def list_buckets(self):
        try:
            buckets = self.client.buckets.list()
            bucket_dict = buckets.dict()
            return bucket_dict
        except Exception as e:
            logger.error(f"Failed to list buckets: {str(e)}")
            return None

    def list_bucket_names(self):
        try:
            response = self.client.buckets.list()
            bucket_names = [bucket.name for bucket in response.buckets]
            return bucket_names
        except Exception as e:
            logger.error(f"Failed to list bucket names: {str(e)}")
            return None

    def list_bucket_ids(self):
        try:
            response = self.list_buckets()
            bucket_ids = [bucket["bucketId"] for bucket in response["buckets"]]
            return bucket_ids
        except Exception as e:
            logger.error(f"Failed to list bucket ids: {str(e)}")
            return None

    def get_bucket_id(self, bucket_name):
        """
        Get a group ID by its name.
        Returns the group_id if found, None otherwise.
        """
        bucket = self.get_bucket_by_name(bucket_name)
        return bucket.bucket_id if bucket else None

    def get_bucket_by_name(self, bucket_name):
        """
        Get a bucket by its name.
        Returns the bucket object if found, None otherwise.
        """
        try:
            response = self.client.buckets.list()
            if not response or not response.buckets:
                logger.info(f"No buckets found")
                return None

            # Find the group with matching name
            for bucket in response.buckets:
                if bucket.name == bucket_name:
                    logger.info(f"Found group '{bucket_name}' with ID: {bucket.bucket_id}")
                    return bucket

            logger.info(f"Bucket '{bucket_name}' not found")
            return None

        except Exception as e:
            logger.error(f"Failed to get group by name '{group_name}': {str(e)}")
            raise

    def delete_bucket(self, id):
        try:
            response = self.client.buckets.delete(
                bucket_id=id,
            )
            return response
        except Exception as e:
            logger.error(f"Failed to delete bucket: {str(e)}")
            return None

    def create_group(self, group_name):
        if group_name is None:
            logger.info("No group name provided")
            return None

        try:
            logger.info(f"Creating group: {group_name}")
            response = self.client.groups.create(name=group_name)
            logger.info(response)
            return response
        except Exception as e:
            logger.error(f"Failed to create group: {str(e)}")
            return None

    def list_buckets_in_group(self):
        try:
            bucket_ids_in_group = [bucket.bucket_id for bucket in self.group.buckets]
            return bucket_ids_in_group
        except Exception as e:
            logger.error(f"Failed to list buckets in group: {str(e)}")
            return None

    def list_groups(self):
        try:
            groups = self.client.groups.list()
            return groups
        except Exception as e:
            logger.error(f"Failed to list groups: {str(e)}")
            return None

    def get_group_id(self, group_name):
        """
        Get a group ID by its name.
        Returns the group_id if found, None otherwise.
        """
        group = self.get_group_by_name(group_name)
        return group.group_id if group else None

    def get_group_by_name(self, group_name):
        """
        Get a group by its name.
        Returns the group object if found, None otherwise.
        """
        try:
            response = self.list_groups()
            if not response or not response.groups:
                logger.info(f"No groups found")
                return None

            # Find the group with matching name
            for group in response.groups:
                if group.name == group_name:
                    logger.info(f"Found group '{group_name}' with ID: {group.group_id}")
                    return group

            logger.info(f"Group '{group_name}' not found")
            return None

        except Exception as e:
            logger.error(f"Failed to get group by name '{group_name}': {str(e)}")
            raise

    def add_bucket_to_group(self, group_name, bucket_id):
        group_id = self.get_group_id(group_name)
        response = self.client.groups.add_bucket(
            group_id=group_id,
            bucket_id=bucket_id,
        )
        if not response.message == "OK":
            raise Exception(f"Failed to add bucket to group '{group_name}': {response.message}")

        return response

    def list_group_names(self):
        try:
            response = self.client.groups.list()
            if response.groups:
                group_name_list = [group.name for group in response.groups]
                return group_name_list
            else:
                # Could be empty
                return None

        except BadRequestError as e:
            logger.error(f"Failed to list group names: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Failed to list group names: {str(e)}")
            raise e

    def search_content(self, query, n=20, next_token=None, verbosity=1, relevance=10.0, search_filter=None):
        """
        Search for content across all buckets in the group

        Args:
            query: The search query string
            n: Maximum number of results (1-100, default 20)
            next_token: Token for pagination
            verbosity: 0=context only, 1=results without searchData, 2=full results
            relevance: Minimum relevance score (default 10.0)
            search_filter: Optional key-value pairs for pre-filtering

        Returns:
            SearchResponse object with results and context
        """
        try:
            # Use the group ID to search across all buckets in the group
            response = self.client.search.content(
                id=self.group_id,
                query=query,
                n=n,
                next_token=next_token,
                verbosity=verbosity,
                relevance=relevance,
                filter=search_filter
            )
            return response
        except Exception as e:
            logger.error(f"Failed to search content: {str(e)}")
            raise

    def get_search_context(self, query, n=20):
        """
        Get search context optimized for LLM usage (simplified method)

        Returns just the text context for direct LLM usage
        """
        try:
            response = self.search_content(query=query, n=n, verbosity=0)
            # The search object has a 'text' attribute directly
            if response and hasattr(response, 'search') and response.search:
                return response.search.text
            return None
        except Exception as e:
            logger.error(f"Failed to get search context: {str(e)}")
            return None

    def get_search_results_with_citations(self, query, n=20):
        """
        Get search results with full citation information

        Returns structured results for building citations
        """
        try:
            response = self.search_content(query=query, n=n, verbosity=2)

            if not response or not hasattr(response, 'search'):
                logger.warning(f"No search results found for query: {query}")
                return None

            search_obj = response.search

            # Format results for easy citation usage
            citations = []
            if hasattr(search_obj, 'results') and search_obj.results:
                for result in search_obj.results:
                    citation = {
                        'text': result.text if hasattr(result, 'text') else '',
                        'suggested_text': result.suggested_text if hasattr(result, 'suggested_text') else '',
                        'source_url': result.source_url if hasattr(result, 'source_url') else '',
                        'file_name': result.file_name if hasattr(result, 'file_name') else '',
                        'document_id': result.document_id if hasattr(result, 'document_id') else '',
                        'bucket_id': result.bucket_id if hasattr(result, 'bucket_id') else '',
                        'score': result.score if hasattr(result, 'score') else 0,
                        'page_images': result.page_images if hasattr(result, 'page_images') else [],
                        'bounding_boxes': result.bounding_boxes if hasattr(result, 'bounding_boxes') else [],
                        'json': result.json if hasattr(result, 'json') else None  # For structured table data
                    }
                    citations.append(citation)

            return {
                'context': search_obj.text if hasattr(search_obj, 'text') else '',
                'citations': citations,
                'query': search_obj.query if hasattr(search_obj, 'query') else query,
                'next_token': search_obj.next_token if hasattr(search_obj, 'next_token') else None,
                'total_results': search_obj.count if hasattr(search_obj, 'count') else len(citations)
            }

        except Exception as e:
            logger.error(f"Failed to get search results with citations: {str(e)}")
            return None
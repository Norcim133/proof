from llama_cloud.client import LlamaCloud
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.indices.managed.llama_cloud import LlamaCloudCompositeRetriever
from llama_cloud.types import CloudSharepointDataSource, PresetRetrievalParams
from llama_cloud import RetrieverCreate, RetrieverPipeline
from llama_cloud import CompositeRetrievalMode, ReRankConfig, ReRankerType
import tempfile
import os
from typing import Optional, List, Dict
import json
import logging
from errors import *
import httpx

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, llama_cloud_api_key):
        try:
            self.api_key = llama_cloud_api_key
            self.client = LlamaCloud(token=self.api_key)
            self.file_id_name_dict = None
            self.composite_retriever_name = "Composite Retriever"
            self.composite_image_retriever_name = "Composite Image Retriever"
            self.existing_retriever_names_list = None
            self.composite_retriever = None
            self.composite_image_retriever = None

        except Exception as e:
            logging.error(f"Failed to initialize LlamaCloud client: {str(e)}")
            raise e

        try:
            self._organization_id = self._get_org_id()
        except Exception as e:
            self._organization_id = None
            logging.error(f"Failed to get organization ID during init: {e}")
            raise OrgNotFoundError(f"Failed to get organization ID during init") from e

        try:
            self._project_id = self._get_first_project_id()
        except Exception as e:
            self._project_id = None
            logging.error(f"Failed to get project ID during init: {e}")
            raise ProjectNotFoundError(f"Failed to get project ID during init") from e

        try:
            self.file_id_name_dict = self.list_filename_to_id_dict()
        except Exception as e:
            logging.error(f"Failed to list filename dict during init: {e}")
            raise e

        try:
            self._indices = self.list_llama_indices()
        except Exception as e:
            self._indices = None
            logging.error(f"Failed to get indices during init: {e}")
            raise IndexRetrievalError(f"Failed to get indices during init") from e

        try:
            self.existing_retriever_names_list = self._list_retriever_names()
        except Exception as e:
            logging.error(f"Failed to list existing retrievers during init: {e}")
            raise RetrieverFailedError(f"Failed to list existing retrievers during init") from e

        try:
            self.composite_retriever = self._build_retriever()
        except Exception as e:
            self.composite_retriever = None
            logging.error(f"Failed to get composite retriever during init: {e}")
            raise RetrieverFailedError(f"Failed to get composite retriever during init") from e

        try:
            self.composite_image_retriever = self._build_retriever(handle_images=True)
        except Exception as e:
            self.composite_retriever = None
            logging.error(f"Failed to get composite retriever during init: {e}")
            raise RetrieverFailedError(f"Failed to get composite retriever during init") from e

    def _list_retriever_names(self):
        existing_retriever_names = [retriever.name for retriever in self.list_retrievers(raw_response=True)]

        return existing_retriever_names

    def run_retriever_sync(self):
        logger.info(f"Running retriever sync")
        try:
            self._sync_indices_with_retriever(self.composite_retriever)
        except Exception as e:
            logging.error(f"Failed to sync composite retriever: {e}")
            raise RetrieverFailedError(f"Failed to sync composite retriever: {e}")
        try:
            self._sync_indices_with_retriever(self.composite_image_retriever)
        except Exception as e:
            logging.error(f"Failed to sync image composite retriever: {e}")
            raise RetrieverFailedError(f"Failed to sync image composite retriever: {e}")


    def _sync_indices_with_retriever(self, composite_retriever):
        try:
            index_object_list = self._build_indices()

            for index in index_object_list:
                description = ""
                pipeline_id = getattr(index, "id")
                files = self.list_pipeline_files(pipeline_id=pipeline_id, raw_response=False)
                for ids, contents in files.items():
                    description += contents['path']

                if composite_retriever.name == self.composite_image_retriever_name:
                    handle_images = True
                else:
                    handle_images = False

                #Figures out if was set to multimodal retrieval in init
                if handle_images:
                    pipeline_metadata = self.get_pipeline(pipeline_id=pipeline_id)
                    take_screenshot_setting = pipeline_metadata.llama_parse_parameters.take_screenshot
                    if take_screenshot_setting:
                        retrieve_image_nodes = True
                    else:
                        retrieve_image_nodes = False
                else:
                    retrieve_image_nodes = False

                pipeline_specific_retrieval_params = PresetRetrievalParams(
                    retrieve_image_nodes=retrieve_image_nodes,)

                composite_retriever.add_index(index=index, preset_retrieval_parameters=pipeline_specific_retrieval_params)
                logger.info(f"Added index {description} to pipeline")
            return composite_retriever
        except Exception as e:
            logger.error(f"Failed to get composite retriever during init: {e}")
            raise RetrieverFailedError(f"Failed to get composite retriever during init") from e

    def _build_retriever(self, handle_images=False):
        try:
            if handle_images:
                name = self.composite_image_retriever_name
            else:
                name = self.composite_retriever_name
            composite_retriever = LlamaCloudCompositeRetriever(
                name=name,
                project_id=self.project_id,
                organization_id=self.organization_id,
                create_if_not_exists=True,
                # CompositeRetrievalMode.FULL will query each index individually and globally rerank results at the end
                # CompositeRetrievalMode.ROUTED an agent determines which sub-indices are most relevant to the provided query (based on the sub-index's name & description you've provided)
                mode=CompositeRetrievalMode.FULL,
                rerank_top_n=5,
            )

            if name in self.existing_retriever_names_list:
                return composite_retriever
            else:
                composite_retriever = self._sync_indices_with_retriever(composite_retriever=composite_retriever)

                return composite_retriever
        except Exception as e:
            logger.error(f"Failed to get composite retriever during init: {e}")
            raise RetrieverFailedError(f"Failed to get composite retriever during init") from e

    def _build_indices(self):
        """Build local index objects for use in local retriever"""
        index_object_list = []
        for name, index_id in self.indices.items():
            index = LlamaCloudIndex(
                name=name,
                project_id=self.project_id,
                api_key=self.api_key,
                organization_id=self.organization_id
            )
            index_object_list.append(index)

        return index_object_list

    def _get_org_id(self):
        try:
            org_object = self.client.organizations.get_default_organization()
            if not org_object:
                logging.info("_get_org_id returned []")
                raise OrgNotFoundError("Response from client was empty")
            org_id = org_object.id
            return org_id
        except Exception as e:
            logging.error(f"Failed to get organization ID: {e}")
            raise

    @property
    def organization_id(self):
        return self._organization_id

    @property
    def project_id(self):
        return self._project_id

    @property
    def indices(self):
        return self._indices

    def _get_first_project_id(self):
        try:
            project_ids = self.list_llama_projects()
            if not project_ids:
                logging.info("GET_FIRST_PROJECT_ID: _get_first_project_id returned []")
                raise ProjectNotFoundError("No project IDs returned")
            keys = project_ids.keys()
            first_project_id = project_ids[next(iter(keys))]
            return first_project_id
        except Exception as e:
            raise CriticalInitializationError(f"GET_FIRST_PROJECT_ID: Failed to get first project ID: {e}")

    def list_llama_projects(self):
        if self.organization_id is None:
            raise MissingValueError("No organization ID set in client")
        try:
            projects = self.client.projects.list_projects(organization_id=self.organization_id)

            if projects:
                project_dict = {}
                for project in projects:
                    project_dict[project.name] = project.id
                return project_dict
            else:
                logging.warning("LIST_LLAMA_PROJECTS: No projects found")
                raise ProjectNotFoundError("No projects found")
        except Exception as e:
            logging.error(f"Failed to list projects: {str(e)}")
            raise

    def list_llama_indices(self) -> Dict:
        """List existing LlamaCloud indices/pipelines"""

        if self._project_id is None:
            logging.warning("LIST_LLAMA_INDICES: No llama_project_id")
            raise MissingValueError("No llama_project_id in list_llama_indices")

        try:
            pipelines = self.client.pipelines.search_pipelines(project_id=self._project_id)
        except Exception as e:
            raise LlamaOperationFailedError(f"LIST_LLAMA_INDICES: Failed to list pipelines: {str(e)}")

        if not pipelines:
            logging.warning("LIST_LLAMA_INDICES: No pipelines have been created")
            return {}

        pipeline_dict = {}
        for pipeline in pipelines:
            pipeline_dict[pipeline.name] = pipeline.id
        return pipeline_dict

    def get_pipeline(self, pipeline_id):
        if pipeline_id is None:
            raise MissingValueError("get_pipeline: No pipeline_id provided")
        try:
            response = self.client.pipelines.get_pipeline(pipeline_id=pipeline_id)
            return response
        except Exception as e:
            return f"Error getting pipeline {e}"

    def get_data_sources_id_map(self, raw_mode=False):
        response = self.client.data_sources.list_data_sources(organization_id=self.organization_id)
        if len(response) == 0:
            return "No data sources found"

        result = ""

        result += "Existing LlamaCloud data sources:\n"
        source_dict = {}
        for source in response:
            source_dict[source.name] = source.id
            source_dict[source.id] = source.name
            if raw_mode:
                return source_dict
            result += json.dumps(source_dict, indent=4)
        return result

    def create_sharepoint_data_source(self, folder_path, folder_id, name_for_source, site_name, client_id, client_secret, tenant_id):
        """Connects llamacloud to a specific sharepoint directory"""
        try:

            site_name = site_name
            client_id = client_id
            client_secret = client_secret
            tenant_id = tenant_id
            folder_path = folder_path
            folder_id = folder_id
            name = name_for_source

            ds = {
                'name': name,
                'source_type': 'MICROSOFT_SHAREPOINT',
                'component': CloudSharepointDataSource(
                    site_name=site_name,
                    folder_path=folder_path,
                    client_id=client_id,
                    client_secret=client_secret,
                    tenant_id=tenant_id,
                    folder_id=folder_id,
                )
            }
            data_source = self.client.data_sources.create_data_source(request=ds)

            return data_source
        except Exception as e:
            return f"Possible .env variables not set with Azure credentials required for data source: {e}"

    def get_data_source(self, data_source_id):
        if data_source_id is None:
            return "You must supply data_source_id to get data_source"

        data_source = self.client.data_sources.get_data_source(data_source_id=data_source_id)

        if data_source is None:
            return "Failed to get data source"

        return data_source

    def get_pipeline_datasources(self, pipeline_id: str):
        try:
            response = self.client.pipelines.list_pipeline_data_sources(pipeline_id=pipeline_id)
            return response
        except Exception as e:
            return f"Failed to get pipelines data sources: {e}"

    def add_data_source_to_pipeline(self, pipeline_id: str, data_source_id: str, sync_interval: float = 43200.0):
        data_sources = [
            {
                'data_source_id': data_source_id,
                'sync_interval': sync_interval #default12 hours re-sync interval
            }
        ]
        try:
            response = self.client.pipelines.add_data_sources_to_pipeline(pipeline_id=pipeline_id, request=data_sources)
            return response
        except Exception as e:
            return f"Failed to add data sources to pipeline: {e}"

    def _format_file_response(self, files):
        try:
            result = ""
            files_dict = {}
            if files:
                for file in files:
                    files_dict[file.id] = {}
                    files_dict[file.id]['path'] = file.name
                    files_dict[file.id]['content_url'] = file.resource_info.get('url', None)
                return files_dict
            else:
                logging.warning("LIST_LLAMA_INDICES: No files found")
                return None
        except Exception as e:
            raise LlamaOperationFailedError(f"Failed to format files: {e}")

    def list_available_llama_files(self, raw_response=False):

        organization_id = self.organization_id

        try:
            files = self.client.files.list_files(organization_id=organization_id)
            if raw_response:

                return files

            result = self._format_file_response(files)

            return result
        except Exception as e:
            logging.error(e)
            return f"Failed to list available Llama files: {e}"

    def list_pipeline_files(self, pipeline_id: str, raw_response=False):
        try:
            files = self.client.pipelines.list_pipeline_files(pipeline_id=pipeline_id)
            if raw_response:
                return files
            result = self._format_file_response(files)

            return result
        except Exception as e:
            logging.error(e)
            return f"Failed to list available pipeline files: {e}"

    def list_filename_to_id_dict(self):
        files = self.client.files.list_files(organization_id=self.organization_id)
        name_to_id_dict = {}
        for file in files:
            name_to_id_dict[file.name] = file.id
            name_to_id_dict[file.id] = file.name
        return name_to_id_dict


    def search_index(self, pipeline_id: str, query: str = ""):
        try:
            result = self.client.pipelines.run_search(pipeline_id=pipeline_id, query=query)

            response_text = f"Search results for '{query}':\n\n"

            for i, node in enumerate(result.retrieval_nodes, 1):
                response_text += f"Result {i} (Score: {node.score:.3f}):\n"
                response_text += f"Source: {node.node.extra_info.get('file_name', 'Unknown')}\n"
                response_text += f"Content: {node.node.text}\n\n"

            return response_text
        except Exception as e:
            logging.error(e)
            return f"Failed to search index: {e}"

    def sync_pipeline(self, pipeline_id:str):
        try:
            response = self.client.pipelines.sync_pipeline(pipeline_id=pipeline_id)
            return response
        except Exception as e:
            logging.error(e)
            return f"Failed to sync pipeline: {e}"

    def create_retriever(self, name: str, pipeline_ids: List[str], project_id: Optional[str] = None):
        """Create a new retriever with specified pipelines"""

        # Build pipeline configurations
        pipelines = []
        for pipeline_id in pipeline_ids:
            pipelines.append(RetrieverPipeline(
                pipeline_id=pipeline_id,
            ))

        # Create the retriever
        request = RetrieverCreate(
            name=name,
            pipelines=pipelines
        )

        retriever = self.client.retrievers.create_retriever(
            project_id=project_id,
            organization_id=self.organization_id,
            request=request
        )

        return retriever

    def list_retrievers(self, raw_response=False):
        """List all retrievers in the project"""

        retrievers = self.client.retrievers.list_retrievers(
            project_id=self.project_id,
            organization_id=self.organization_id
        )
        if raw_response:
            return retrievers
        result = "Existing LlamaCloud Retrievers:\n"
        for retriever in retrievers:
            result += f"- {retriever.name} (ID: {retriever.id})\n"
            if retriever.pipelines:
                for pipeline in retriever.pipelines:
                    result += f"  └─ Pipeline: {pipeline.pipeline_id})\n"

        return result

    def get_retriever(self, retriever_id: str):
        try:
            retriever = self.client.retrievers.get_retriver(retriever_id=retriever_id)
            return retriever
        except Exception as e:
            logger.error(e)
            raise LlamaOperationFailedError(f"Failed to get retriever: {e}")

    def delete_retriever(self, retriever_id: str):
        try:
            response = self.client.retrievers.delete_retriever(retriever_id=retriever_id)
            return response
        except Exception as e:
            logger.error(e)
            raise LlamaOperationFailedError(f"Failed to delete retriever: {e}")

    def retrieve_with_retriever(self,
                                      retriever_id: str,
                                      query: str,
                                      mode: str = "routing",
                                      rerank_top_n: Optional[int] = None):
        """Retrieve using an existing retriever"""

        # Map string mode to enum - only FULL and ROUTING are available
        mode_map = {
            "routing": CompositeRetrievalMode.ROUTING,
            "full": CompositeRetrievalMode.FULL
        }

        composite_mode = mode_map.get(mode.lower(), CompositeRetrievalMode.FULL)

        # Configure reranking
        rerank_config = ReRankConfig(type=ReRankerType.SYSTEM_DEFAULT)

        # Execute retrieval
        result = self.client.retrievers.retrieve(
            retriever_id=retriever_id,
            mode=composite_mode,
            rerank_top_n=rerank_top_n,
            rerank_config=rerank_config,
            query=query
        )

        return self._format_composite_retrieval_result(result)

    def direct_retrieve(self,
                              pipeline_ids: List[str],
                              query: str,
                              mode: str = "routing",
                              rerank_top_n: Optional[int] = None,
                              top_k_per_pipeline: int = 10,
                              project_id: Optional[str] = None):
        """Retrieve directly without creating a persistent retriever"""

        # CompositeRetrievalMode is already an enum, just use it directly
        mode_enum = CompositeRetrievalMode.ROUTING
        if mode.lower() == "full":
            mode_enum = CompositeRetrievalMode.FULL

        # Build pipeline configurations as simple dicts with required fields
        pipelines = []
        for i, pipeline_id in enumerate(pipeline_ids):
            pipelines.append({
                "pipeline_id": pipeline_id,
                "name": f"pipeline_{i}",
                "description": f"Pipeline {i} for retrieval",
                "top_k": top_k_per_pipeline
            })

        # Execute retrieval
        result = self.client.retrievers.direct_retrieve(
            project_id=project_id,
            organization_id=self.organization_id,
            mode=mode_enum,
            rerank_top_n=rerank_top_n,
            query=query,
            pipelines=pipelines
        )

        return self._format_composite_retrieval_result(result)

    def _format_composite_retrieval_result(self, result):
        """Format the retrieval result as simple chunks for RAG"""
        nodes = result.nodes if hasattr(result, 'nodes') else []

        formatted = f"Retrieved {len(nodes)} chunks:\n\n"

        for i, node in enumerate(nodes, 1):
            # Extract metadata safely
            metadata = node.node.metadata if hasattr(node.node, 'metadata') else {}

            formatted += f"--- Chunk {i} ---\n"
            formatted += f"Score: {node.score:.4f}\n"
            formatted += f"File: {metadata.get('file_name', 'Unknown')}\n"
            formatted += f"Path: {metadata.get('file_path', 'Unknown')}\n"
            formatted += f"Text: {node.node.text[:300]}...\n\n"

        return formatted

    def check_pipeline_status(self, pipeline_id: str):
        """Check the status of a pipeline's latest job"""
        response = self.client.pipelines.get_pipeline_status(pipeline_id=pipeline_id)
        return f"Pipeline {pipeline_id}: {response.status.value} (Job: {response.job_id})"

    def check_all_pipeline_statuses(self, raw_response=False):
        """Check status of all pipelines in a project"""

        project_id = self.project_id
        pipelines = self.client.pipelines.search_pipelines(project_id=project_id)

        results = []
        for pipeline in pipelines:
            try:
                status = self.client.pipelines.get_pipeline_status(pipeline_id=pipeline.id)
                if raw_response:
                    results.append(f"{pipeline.name}: {status}")
                else:
                    results.append(f"{pipeline.name}: {status.status.value}")

            except:
                results.append(f"{pipeline.name}: ERROR")

        return "\n".join(results)

    def upload_sharepoint_file_to_llamacloud(self,
                                                   sharepoint_drive_id: str,
                                                   sharepoint_file_id: str,
                                                   graph_client,  # Need the graph client to download
                                                   project_id: Optional[str] = None):
        """Download from SharePoint and upload to LlamaCloud"""


        # Get file info from SharePoint
        file_info = graph_client.drives.by_drive_id(sharepoint_drive_id).items.by_drive_item_id(
            sharepoint_file_id).get()
        file_name = file_info.name

        # Download file content from SharePoint
        file_content = graph_client.drives.by_drive_id(sharepoint_drive_id).items.by_drive_item_id(
            sharepoint_file_id).content.get()

        # Create temp directory and save with original filename
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file_name)

        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(file_content)

        try:
            # Upload to LlamaCloud
            with open(temp_file_path, 'rb') as file_to_upload:
                uploaded_file = self.client.files.upload_file(
                    project_id=project_id,
                    organization_id=self.organization_id,
                    upload_file=file_to_upload,
                    external_file_id=f"sharepoint/{sharepoint_drive_id}/{sharepoint_file_id}"  # Track source
                )

            return f"Uploaded {file_name} to LlamaCloud. File ID: {uploaded_file.id}"

        finally:
            # Clean up temp file and directory
            os.unlink(temp_file_path)
            os.rmdir(temp_dir)

    def list_file_screenshots(self, file_id: str):
        """List all page screenshots available for a file"""
        screenshots = self.client.files.list_file_page_screenshots(
            id=file_id,
            organization_id=self.organization_id
        )
        return screenshots

    def get_file_screenshot(self, file_id: str, page_index: int):
        """Get a specific page screenshot from a file"""
        try:
            # Try the normal API call
            screenshot_data = self.client.files.get_file_page_screenshot(
                id=file_id,
                page_index=page_index,
                organization_id=self.organization_id
            )
            return screenshot_data
        except Exception as e:
            # If it fails due to JSON parsing, we need to get the raw bytes
            # The LlamaCloud client has a bug where it tries to parse image data as JSON

            # Use httpx directly to make the request

            url = f"https://api.cloud.llamaindex.ai/api/v1/files/{file_id}/page_screenshots/{page_index}"

            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "X-Organization-Id": self.organization_id
                    }
                )
                response.raise_for_status()

                # Get the raw bytes
                image_bytes = response.content

                # Log some debug info
                print(f"Image size: {len(image_bytes)} bytes")
                print(f"First 10 bytes: {image_bytes[:10].hex()}")

                return image_bytes

    def get_file_content_url(self, file_id: str, expires_in_seconds: int = 3600):
        """Get a presigned URL to download the file content"""
        try:
            presigned_url = self.client.files.read_file_content(
                id=file_id,
                expires_at_seconds=expires_in_seconds,
                organization_id=self.organization_id
            )

            return presigned_url.url
        except Exception as e:
            logger.error(f"GET_FILE_CONTENT_URL: Error using file_id {file_id} to get content url: {e}")


    def create_pipeline(self,
                              name: str,
                              project_id: Optional[str] = None,
                              pipeline_config: dict = None):
        """
        Create a new pipeline with provided configuration

        Args:
            name: Name for the pipeline
            project_id: Project ID (defaults to env var)
            pipeline_config: Full pipeline configuration dict
        """
        if project_id is None:
            project_id = self.project_id

        if pipeline_config is None:
            pipeline_config = {}

        # Ensure name is in the config
        pipeline_config['name'] = name

        try:
            pipeline = self.client.pipelines.create_pipeline(
                project_id=project_id,
                organization_id=self.organization_id,
                request=pipeline_config
            )

            return f"Created pipeline '{pipeline.name}' with ID: {pipeline.id}\nConfiguration: {json.dumps(pipeline_config, indent=2)}"
        except Exception as e:
            return f"Error creating pipeline: {str(e)}"

    def update_pipeline(self,
                              pipeline_id: str,
                              update_config: dict = None):
        """
        Update an existing pipeline with provided configuration

        Args:
            pipeline_id: ID of pipeline to update
            update_config: Configuration updates to apply
        """
        if update_config is None:
            update_config = {}

        try:
            # The update method expects specific parameters
            pipeline = self.client.pipelines.update_existing_pipeline(
                pipeline_id=pipeline_id,
                **update_config  # Unpack the config dict as kwargs
            )

            return f"Updated pipeline '{pipeline.name}' (ID: {pipeline.id})\nUpdates applied: {json.dumps(update_config, indent=2)}"
        except Exception as e:
            return f"Error updating pipeline: {str(e)}"


    def add_files_to_pipeline(self,
                                    pipeline_id: str,
                                    file_ids: List[str]) -> str:
        """
        Add files to a pipeline for processing

        Args:
            pipeline_id: ID of the pipeline to add files to
            file_ids: List of file IDs to add to the pipeline
        """
        try:
            # Create PipelineFileCreate objects for each file
            file_requests = []
            for file_id in file_ids:
                # PipelineFileCreate typically just needs the file_id
                file_requests.append({
                    'file_id': file_id
                })

            # Add files to pipeline
            result = self.client.pipelines.add_files_to_pipeline_api(
                pipeline_id=pipeline_id,
                request=file_requests
            )

            # Format response
            response = f"Successfully added {len(result)} files to pipeline {pipeline_id}:\n"
            for file in result:
                response += f"  - File ID: {file.id}\n"

            return response

        except Exception as e:
            return f"Error adding files to pipeline: {str(e)}"

    def rename_pipeline(self, new_name:str, pipeline_id:str):
        logging.error(f"Renaming pipeline '{new_name}'")
        if new_name is None or pipeline_id is None:
            logging.warning("No name passed to rename_pipeline")
            raise MissingValueError("No name was submitted to rename_pipeline")

        try:
            response = self.client.pipelines.update_existing_pipeline(
                pipeline_id=pipeline_id,
                name=new_name
            )

            if response.name != new_name:
                raise APIError(f"Error with rename_pipeline. Full response: {response}")
            return response.name
        except Exception as e:
            raise APIError(f"Error with call to update pipeline name: {str(e)}")


    def _parse_files_to_hierarchy(self, files):
        """
        Parse LlamaCloud files into a hierarchical structure
        """
        hierarchy = {
            "data_sources": {},
            "individual_files": []
        }

        for file in files:
            file_info = {
                "id": file.id,
                "name": file.name.split('/')[-1],  # Just the filename
                "url": file.resource_info.get('url', None) if file.resource_info else None,
                "full_path": file.name
            }

            if file.data_source_id:
                # This is from a data source
                ds_id_map = self.get_data_sources_id_map(raw_mode=True)
                ds_name = ds_id_map.get(file.data_source_id)


                # Initialize data source if not exists
                if ds_name not in hierarchy["data_sources"]:
                    hierarchy["data_sources"][ds_name] = {
                        "name": "All Company Documents",
                        "folders": {}
                    }

                # Parse the path
                path_parts = file.name.split('/')
                if len(path_parts) > 2:  # Has folder structure
                    folder_name = path_parts[1]  # Assuming "All Company/Folder/File"

                    if folder_name not in hierarchy["data_sources"][ds_name]["folders"]:
                        hierarchy["data_sources"][ds_name]["folders"][folder_name] = {
                            "files": []
                        }

                    hierarchy["data_sources"][ds_name]["folders"][folder_name]["files"].append(file_info)

            else:
                # Individual file
                hierarchy["individual_files"].append(file_info)

        # Sort everything alphabetically
        for ds_name in hierarchy["data_sources"]:
            for folder in hierarchy["data_sources"][ds_name]["folders"]:
                hierarchy["data_sources"][ds_name]["folders"][folder]["files"].sort(
                    key=lambda x: x["name"].lower()
                )

        hierarchy["individual_files"].sort(key=lambda x: x["name"].lower())

        return hierarchy

    def list_llama_files_dict(self):
        """List all files in org, parsed hierarchically, by folders"""
        organization_id = self.organization_id

        try:
            files = self.client.files.list_files(organization_id=organization_id)

            return self._parse_files_to_hierarchy(files)

        except Exception as e:
            logging.error(e)
            return f"Failed to list available Llama files: {e}"

    def multi_modal_retrieval(self, query_text: str, pipeline_name):
        if query_text is None or pipeline_name is None:
            raise MissingValueError("Query text or pipeline_id is missing")

        multimodal_index = LlamaCloudIndex(
            name=pipeline_name,
            project_id=self.project_id,
            organization_id=self.organization_id,
            api_key=self.api_key
        )

        # Try with images first
        try:
            retriever = multimodal_index.as_retriever(
                similarity_top_k=5,
                retrieve_image_nodes=True
            )
            nodes_with_scores = retriever.retrieve(query_text)
            return nodes_with_scores
        except Exception as e:
            logging.warning(f"Image retrieval failed, falling back to text-only: {e}")
            # Fallback to text-only retrieval
            try:
                retriever = multimodal_index.as_retriever(
                    similarity_top_k=5,
                    retrieve_image_nodes=False
                )
                nodes_with_scores = retriever.retrieve(query_text)
                return nodes_with_scores
            except Exception as e2:
                logging.error(f"MULTI_MODAL_RETRIEVAL error: {e2}")
                raise e2

    def composite_retrieval(self, query_text: str):
        if query_text is None:
            raise MissingValueError("Query text is missing")

        # Try with images first
        try:
            nodes_with_scores = self.composite_retriever.retrieve(query_text)
            return nodes_with_scores
        except Exception as e:
            logging.warning(f"Composite retrieval failed: {e}")
            return None

    def multi_modal_composite_retrieval(self, query_text: str):
        if query_text is None:
            raise MissingValueError("Query text is missing")

        # Try with images first
        try:
            nodes_with_scores = self.composite_image_retriever.retrieve(query_text)
            return nodes_with_scores
        except Exception as e:
            logging.warning(f"Multi modal composite retrieval failed: {e}")
            # Fallback to text-only retrieval
            return None
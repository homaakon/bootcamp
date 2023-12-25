import requests


class BasePipeline:
    def __init__(self):
        self.cloud_region = None
        self.cluster_id = None
        self.api_key = None
        self.pipe_id = None

    def _build_header(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _build_creating_pipeline_url(self):
        return f"https://controller.api.{self.cloud_region}.zillizcloud.com/v1/pipelines"

    def _build_running_pipeline_url(self):
        return f"https://controller.api.{self.cloud_region}.zillizcloud.com/v1/pipelines/{self.pipe_id}/run"


class IngestionPipeline(BasePipeline):
    def __init__(self, cloud_region, cluster_id, api_key, collection_name, pipeline_name, functions,
                 description="A pipeline that splits a text file into chunks and generates embeddings"):
        super().__init__()
        self.cloud_region = cloud_region
        self.cluster_id = cluster_id
        self.api_key = api_key
        self.collection_name = collection_name
        self.pipeline_name = pipeline_name
        self.functions = functions
        self.description = description
        data = {
            "name": self.pipeline_name,
            "description": self.description,
            "type": "INGESTION",
            "functions": self.functions,
            "clusterId": self.cluster_id,
            "newCollectionName": self.collection_name
        }

        response = requests.post(self._build_creating_pipeline_url(),
                                 headers=self._build_header(),
                                 json=data)
        self.pipe_id = response.json()["data"]["pipelineId"]

    def run(self, gcs_url, **kwargs):
        data = {
            "data":
                {
                    "doc_url": f"{gcs_url}",
                    **kwargs,
                }
        }

        response = requests.post(self._build_running_pipeline_url(),
                                 headers=self._build_header(), json=data)

        return response


class SearchPipeline(BasePipeline):
    def __init__(self, cloud_region, api_key, pipeline_name, functions,
                 description="A pipeline that receives text and search for semantically similar doc chunks"):
        super().__init__()
        self.cloud_region = cloud_region
        self.api_key = api_key
        self.pipeline_name = pipeline_name
        self.functions = functions
        self.description = description
        data = {
            "name": self.pipeline_name,
            "description": self.description,
            "type": "SEARCH",
            "functions": self.functions
        }

        response = requests.post(self._build_creating_pipeline_url(),
                                 headers=self._build_header(),
                                 json=data)

        self.pipe_id = response.json()["data"]["pipelineId"]

    def run(self, question, top_k=2, other_output_fields=[], filter=None):
        params = {
            "limit": top_k,
            "offset": 0,
            "outputFields": [
                                "chunk_text",
                                "chunk_id",
                                "doc_name",
                            ] + other_output_fields,
        }
        if filter:
            params['filter'] = filter
        data = {
            "data": {
                "query_text": question
            },
            "params": params
        }
        response = requests.post(self._build_running_pipeline_url(),
                                 headers=self._build_header(), json=data)
        results = response.json()["data"]["result"]
        retrieved_data = []
        for result in results:
            base_data = {'chunk_text': result['chunk_text']}
            for key in other_output_fields:
                base_data[key] = result[key]
            retrieved_data.append(base_data)
        return retrieved_data

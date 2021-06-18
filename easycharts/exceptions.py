from fastapi import HTTPException

class DuplicateDatasetError(HTTPException):
    def __init__(self, dataset: str):
        super().__init__(
            status_code = 422,
            detail = f"A dataset with name {dataset} already exists"
        )
class MissingDatasetError(HTTPException):
    def __init__(self, dataset: str):
        super().__init__(
            status_code = 404,
            detail = f"No dataset with name {dataset} exists"
        )
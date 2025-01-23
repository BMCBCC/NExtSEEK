# backend/app/services/nhp_service.py

from ..utils.helpers import execute_query, get_NHP_name
import json
from typing import List
from ..models.schemas import NHPInfo
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)
cache = {}

def fetch_NHP(term):
    """
    Fetch the NHP metadata for a given term.

    Args:
        term (str): The UUID to search for in the database.

    Returns:
        list: A list of results from the database query.
    """
    try:
        query = """
        SELECT uuid, json_metadata
        FROM seek_production.samples
        WHERE uuid = %s;
        """
        nhp_metadata = execute_query(query, (term,))
        return nhp_metadata
    except Exception as e:
        logger.error(f"Error fetching NHP metadata: {e}")
        return None
    

def fetch_all_nhp_related_data(nhp_name):
    nhp_name = nhp_name.strip()
    # Get base NHP metadata first
    nhp_metadata = fetch_NHP(nhp_name)
    if not nhp_metadata:
        return []
    
    NHP, search_term1 = get_NHP_name(nhp_metadata)  # the original logic to derive the search term
    NHP,search_term2 = get_NHP_name(nhp_metadata, img = True)
    # This search_term should be broad enough to cover PAV, TIS, IMG, etc.
    # e.g., you might use a wildcard search like:
    # "WHERE json_metadata LIKE %s" and pass in search_term from get_NHP_name
    
    # query = """
    # SELECT uuid, json_metadata
    # FROM seek_production.samples
    # WHERE json_metadata LIKE %s OR json_metadata LIKE %s;
    # """

    # search_term1 = f'%{nhp_name}%'

    # query = """
    # SELECT uuid, json_metadata
    # FROM seek_production.samples
    # WHERE json_metadata LIKE %s;
    # """

    query = """
    SELECT uuid, json_metadata
    FROM seek_production.samples
    WHERE 
        (
            uuid LIKE '%D.IMG%FLY%' AND json_metadata LIKE %s
        )
        OR 
        (
            uuid NOT LIKE '%D.IMG%FLY%' AND json_metadata LIKE %s
        );
    """
    all_data = execute_query(query, (search_term2,search_term1))
    print(NHP)
    return all_data, NHP

def get_nhp_data(nhp_name):
    if not nhp_name or not isinstance(nhp_name, str):
        logger.error(f"Invalid NHP name provided: {nhp_name}")
        return []

    logger.debug(f"Using cache key: {nhp_name}")
    if nhp_name in cache:
        logger.debug(f"Cache hit for key: {nhp_name}")
        return cache[nhp_name]
    else:
        logger.debug(f"Cache miss for key: {nhp_name}, fetching data.")

    all_data, name = fetch_all_nhp_related_data(nhp_name)

    # Parse JSON once here
    for entry in all_data:
        # if name in entry["json_metadata"]["Name"]:
        entry['parsed_metadata'] = json.loads(entry['json_metadata'])
    
    uuids = [entry['uuid'] for entry in all_data if "FLY" in entry["parsed_metadata"]["UID"]]
    
    print(uuids[:5])
    print(len(uuids))
    # uuids = [entry['uuid'] for entry in all_data]
    # filter all_data to only include the uuids
    all_data = [entry for entry in all_data if entry['uuid'] in uuids]

    # check if more than 1 entry has a UID that starts with "NHP"
    nhp_uuids = [entry['uuid'] for entry in all_data if entry["parsed_metadata"]["UID"].startswith("NHP")]
    if len(nhp_uuids) > 1:
        print("More than 1 entry has a UID that starts with NHP")
        print(nhp_uuids)

    print(len(all_data))
    nhp_name = nhp_name.strip()
    cache[nhp_name] = all_data
    logger.debug(f"Data for {nhp_name} added to cache.")
    return all_data


def fetch_NHP_PAV(all_data):
    """
    Retrieves the NHP PAV metadata from all_data.

    Args:
        all_data : parsed json_metadata.

    Returns:
        list: A list of results from the database query.
    """
    try:
        results = [entry for entry in all_data if 'PAV' in entry['uuid']]
        return results
    except Exception as e:
        logger.error(f"Error fetching NHP PAV metadata: {e}")
        return []

def fetch_NHP_TIS(all_data):
    """
    Fetch the NHP TIS metadata.

    Args:
        all_data : parsed json_metadata.

    Returns:
        list: A list of results from the database query.
    """
    try:
        results = [entry for entry in all_data if 'TIS' in entry['uuid']]
        return results
    except Exception as e:
        logger.error(f"Error fetching NHP TIS metadata: {e}")
        return None

def fetch_NHP_IMG(all_data):
    """
    Fetch the NHP IMG metadata.

    Args:
        all_data : parsed json_metadata.

    Returns:
        list: A list of results from the database query.
    """
    try:
        results = [entry for entry in all_data if 'D.IMG' in entry['uuid']]
        results = [entry for entry in results if 'FLY' in entry['uuid']]
        uuids = [entry['uuid'] for entry in results]
        print(uuids)
        return results
    except Exception as e:
        logger.error(f"Error fetching NHP IMG metadata: {e}")
        return None

def save_nhp_info_to_json(nhp_name) -> List[NHPInfo]:
    """
    Save NHP metadata to a JSON file.

    Args:
        nhp_name (str): The UID of the NHP.
        filename (str): The name of the file to save the metadata to.

    Returns:
        list: The NHP information saved to the file, or None if an error occurred.
    """
    nhp_metadata = get_nhp_data(nhp_name)
    # print(nhp_metadata[:5])
    if not nhp_metadata:
        logger.error("No metadata found.")
        return []

    processed_data = []

    try:
        uuids = [entry['uuid'] for entry in nhp_metadata]
        idx = uuids.index(nhp_name)
        # print(idx)
        metadata_dict = nhp_metadata[idx]['parsed_metadata']
        logger.info(metadata_dict)
    except json.JSONDecodeError:
        print("Error decoding JSON")
        metadata_dict = {}
        # Process each record and convert to NHPInfo
    try:
        processed_data.append(metadata_dict)
    except ValidationError as ve:
        # Log the validation error and skip the record
        logger.error(f"Validation error: {ve}")

    logger.info(processed_data)

    return processed_data

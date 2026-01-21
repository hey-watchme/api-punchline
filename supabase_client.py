"""
Supabase Client for PUNCHLINE API

Handles database operations for punchline extraction service.
"""

import os
import math
import json
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from datetime import datetime


class SupabaseClient:
    def __init__(self):
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

        self.client: Client = create_client(url, key)
        print(f"Supabase client initialized: {url}")

    async def save_punchline_request(
        self,
        request_id: str,
        conversation_text: str,
        user_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save initial punchline request

        Args:
            request_id: Unique request ID (UUID)
            conversation_text: Full conversation text
            user_id: Optional user ID
            context_data: Optional context (topic, participants, etc.)

        Returns:
            bool: Success status
        """
        try:
            data = {
                'request_id': request_id,
                'conversation_text': conversation_text,
                'user_id': user_id,
                'context_data': context_data or {},
                'created_at': datetime.now().isoformat()
            }

            response = self.client.table('punchline_requests').insert(data).execute()

            if response.data:
                print(f"Saved punchline request: {request_id}")
                return True
            return False

        except Exception as e:
            print(f"Error saving punchline request: {str(e)}")
            raise e

    async def save_structured_conversation(
        self,
        request_id: str,
        structured_result: Dict[str, Any],
        speakers: List[str],
        turn_count: int,
        summary: str
    ) -> bool:
        """
        Save structured conversation from Pipeline 1

        Args:
            request_id: Reference to punchline_requests
            structured_result: Full LLM output
            speakers: List of identified speakers
            turn_count: Number of conversation turns
            summary: Conversation summary

        Returns:
            bool: Success status
        """
        try:
            data = {
                'request_id': request_id,
                'structured_result': structured_result,
                'speakers': speakers,
                'turn_count': turn_count,
                'summary': summary,
                'created_at': datetime.now().isoformat()
            }

            response = self.client.table('punchline_structured_conversations').insert(data).execute()

            if response.data:
                print(f"Saved structured conversation for request: {request_id}")
                return True
            return False

        except Exception as e:
            print(f"Error saving structured conversation: {str(e)}")
            raise e

    async def save_punchline_results(
        self,
        request_id: str,
        punchlines: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        llm_model: str
    ) -> bool:
        """
        Save extracted punchlines from Pipeline 2

        Args:
            request_id: Reference to punchline_requests
            punchlines: List of extracted punchlines with scores
            metadata: Processing metadata (time, model, etc.)
            llm_model: Model used for extraction

        Returns:
            bool: Success status
        """
        try:
            # Sanitize values to handle NaN/Infinity
            def sanitize_value(value):
                if isinstance(value, float):
                    if math.isnan(value) or math.isinf(value):
                        return None
                return value

            def sanitize_dict(d):
                if d is None:
                    return {}
                result = {}
                for key, value in d.items():
                    if isinstance(value, list):
                        result[key] = [sanitize_dict(item) if isinstance(item, dict) else sanitize_value(item) for item in value]
                    elif isinstance(value, dict):
                        result[key] = sanitize_dict(value)
                    else:
                        result[key] = sanitize_value(value)
                return result

            # Sanitize punchlines
            sanitized_punchlines = []
            for p in punchlines:
                if isinstance(p, dict):
                    sanitized_punchlines.append(sanitize_dict(p))
                else:
                    sanitized_punchlines.append(p)

            data = {
                'request_id': request_id,
                'punchlines': sanitized_punchlines,
                'metadata': sanitize_dict(metadata),
                'llm_model': llm_model,
                'created_at': datetime.now().isoformat()
            }

            # Verify JSON serialization
            try:
                json.dumps(data)
            except (TypeError, ValueError) as json_error:
                print(f"JSON serialization error: {json_error}")
                raise ValueError(f"Data cannot be converted to JSON: {json_error}")

            response = self.client.table('punchline_results').insert(data).execute()

            if response.data:
                print(f"Saved punchline results for request: {request_id}")
                return True
            return False

        except Exception as e:
            print(f"Error saving punchline results: {str(e)}")
            raise e

    async def get_request_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full request data by request_id

        Args:
            request_id: Unique request ID

        Returns:
            Optional[Dict]: Request data with all related information
        """
        try:
            # Get base request
            request_response = self.client.table('punchline_requests').select('*').eq('request_id', request_id).execute()

            if not request_response.data or len(request_response.data) == 0:
                print(f"No request found for ID: {request_id}")
                return None

            result = request_response.data[0]

            # Get structured conversation
            struct_response = self.client.table('punchline_structured_conversations').select('*').eq('request_id', request_id).execute()

            if struct_response.data and len(struct_response.data) > 0:
                result['structured_conversation'] = struct_response.data[0]

            # Get punchline results
            punchline_response = self.client.table('punchline_results').select('*').eq('request_id', request_id).execute()

            if punchline_response.data and len(punchline_response.data) > 0:
                result['punchline_results'] = punchline_response.data[0]

            return result

        except Exception as e:
            print(f"Error fetching request data: {str(e)}")
            raise e

    async def get_user_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's request history

        Args:
            user_id: User ID
            limit: Maximum number of results

        Returns:
            List[Dict]: List of user's requests
        """
        try:
            response = self.client.table('punchline_requests').select(
                'request_id, created_at, context_data'
            ).eq(
                'user_id', user_id
            ).order(
                'created_at', desc=True
            ).limit(limit).execute()

            if response.data:
                # Enrich with result counts
                results = []
                for request in response.data:
                    # Get punchline count for this request
                    punchline_response = self.client.table('punchline_results').select(
                        'punchlines'
                    ).eq('request_id', request['request_id']).execute()

                    punchline_count = 0
                    if punchline_response.data and len(punchline_response.data) > 0:
                        punchlines = punchline_response.data[0].get('punchlines', [])
                        punchline_count = len(punchlines)

                    results.append({
                        'request_id': request['request_id'],
                        'created_at': request['created_at'],
                        'context': request.get('context_data', {}),
                        'punchline_count': punchline_count
                    })

                return results

            return []

        except Exception as e:
            print(f"Error fetching user history: {str(e)}")
            raise e

    async def get_watchme_transcription(
        self,
        device_id: str,
        local_date: str,
        local_time: Optional[str] = None
    ) -> Optional[str]:
        """
        Get transcription from WatchMe spot_features table

        Args:
            device_id: Device ID (UUID)
            local_date: Local date (YYYY-MM-DD)
            local_time: Optional local time to match specific recording

        Returns:
            Optional[str]: vibe_transcriber_result text or None if not found
        """
        try:
            # Start with base query
            query = self.client.table('spot_features').select(
                'vibe_transcriber_result, local_time, recorded_at'
            ).eq(
                'device_id', device_id
            ).eq(
                'local_date', local_date
            )

            # Add local_time filter if provided
            if local_time:
                query = query.eq('local_time', local_time)

            # Order by recorded_at to get most recent if multiple matches
            query = query.order('recorded_at', desc=True).limit(1)

            response = query.execute()

            if response.data and len(response.data) > 0:
                transcription = response.data[0].get('vibe_transcriber_result')
                local_time_found = response.data[0].get('local_time', 'N/A')
                print(f"Found transcription for device {device_id} on {local_date} at {local_time_found}")
                return transcription
            else:
                print(f"No transcription found for device {device_id} on {local_date}")
                return None

        except Exception as e:
            print(f"Error fetching WatchMe transcription: {str(e)}")
            raise e

    async def get_watchme_emotions(
        self,
        device_id: str,
        local_date: str,
        local_time: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get Hume emotional data from WatchMe spot_features table

        Args:
            device_id: Device ID (UUID)
            local_date: Local date (YYYY-MM-DD)
            local_time: Optional local time to match specific recording

        Returns:
            Optional[Dict]: emotion_features_result_hume data or None if not found
        """
        try:
            # Start with base query
            query = self.client.table('spot_features').select(
                'emotion_features_result_hume, local_time, recorded_at'
            ).eq(
                'device_id', device_id
            ).eq(
                'local_date', local_date
            )

            # Add local_time filter if provided
            if local_time:
                query = query.eq('local_time', local_time)

            # Order by recorded_at to get most recent if multiple matches
            query = query.order('recorded_at', desc=True).limit(1)

            response = query.execute()

            if response.data and len(response.data) > 0:
                emotion_data = response.data[0].get('emotion_features_result_hume')
                local_time_found = response.data[0].get('local_time', 'N/A')
                print(f"Found Hume emotions for device {device_id} on {local_date} at {local_time_found}")

                # Parse JSON string if needed
                if isinstance(emotion_data, str):
                    try:
                        return json.loads(emotion_data)
                    except json.JSONDecodeError:
                        print("Warning: Could not parse Hume emotion data as JSON")
                        return None
                return emotion_data
            else:
                print(f"No Hume emotions found for device {device_id} on {local_date}")
                return None

        except Exception as e:
            print(f"Error fetching WatchMe emotions: {str(e)}")
            raise e
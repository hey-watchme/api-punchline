"""
WatchMe Integration Module
============================
Fetches transcription data from WatchMe's spot_features table
and prepares it for punchline extraction
"""

import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class WatchMeIntegration:
    """Handle integration with WatchMe's spot_features data"""

    def __init__(self, supabase_client: Client):
        """
        Initialize WatchMe integration

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def fetch_transcriptions(
        self,
        device_id: str,
        local_date: str,
        limit: int = 48
    ) -> List[Dict]:
        """
        Fetch transcriptions from spot_features table

        Args:
            device_id: Device identifier
            local_date: Local date in YYYY-MM-DD format
            limit: Maximum number of records to fetch (default 48 = one day)

        Returns:
            List of transcription records with metadata
        """
        try:
            # Query spot_features table
            response = self.supabase.table('spot_features')\
                .select('device_id,recorded_at,local_date,local_time,vibe_transcriber_result')\
                .eq('device_id', device_id)\
                .eq('local_date', local_date)\
                .not_.is_('vibe_transcriber_result', 'null')\
                .order('recorded_at', desc=False)\
                .limit(limit)\
                .execute()

            if not response.data:
                logger.warning(f"No transcriptions found for device {device_id} on {local_date}")
                return []

            # Filter out empty transcriptions
            valid_records = []
            for record in response.data:
                transcription = record.get('vibe_transcriber_result', '').strip()
                if transcription and len(transcription) > 10:  # Minimum meaningful length
                    valid_records.append({
                        'device_id': record['device_id'],
                        'recorded_at': record['recorded_at'],
                        'local_date': record['local_date'],
                        'local_time': record['local_time'],
                        'transcription': transcription
                    })

            logger.info(f"Fetched {len(valid_records)} valid transcriptions for device {device_id}")
            return valid_records

        except Exception as e:
            logger.error(f"Error fetching transcriptions: {str(e)}")
            raise

    async def fetch_date_range(
        self,
        device_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Fetch transcriptions for a date range

        Args:
            device_id: Device identifier
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of transcription records across multiple days
        """
        try:
            response = self.supabase.table('spot_features')\
                .select('device_id,recorded_at,local_date,local_time,vibe_transcriber_result')\
                .eq('device_id', device_id)\
                .gte('local_date', start_date)\
                .lte('local_date', end_date)\
                .not_.is_('vibe_transcriber_result', 'null')\
                .order('recorded_at', desc=False)\
                .execute()

            if not response.data:
                logger.warning(f"No transcriptions found for device {device_id} between {start_date} and {end_date}")
                return []

            # Filter and process records
            valid_records = []
            for record in response.data:
                transcription = record.get('vibe_transcriber_result', '').strip()
                if transcription and len(transcription) > 10:
                    valid_records.append({
                        'device_id': record['device_id'],
                        'recorded_at': record['recorded_at'],
                        'local_date': record['local_date'],
                        'local_time': record['local_time'],
                        'transcription': transcription
                    })

            logger.info(f"Fetched {len(valid_records)} transcriptions across {start_date} to {end_date}")
            return valid_records

        except Exception as e:
            logger.error(f"Error fetching date range transcriptions: {str(e)}")
            raise

    def combine_transcriptions(
        self,
        records: List[Dict],
        session_gap_minutes: int = 60
    ) -> str:
        """
        Combine multiple transcriptions into a single conversation

        Args:
            records: List of transcription records
            session_gap_minutes: Minutes between recordings to consider new session

        Returns:
            Combined conversation text with session markers
        """
        if not records:
            return ""

        # Sort by timestamp
        sorted_records = sorted(records, key=lambda x: x['recorded_at'])

        conversation_parts = []
        current_session = []
        last_timestamp = None
        session_count = 0

        for record in sorted_records:
            # Parse timestamp - handle various ISO format variations
            ts_str = record['recorded_at']
            # Clean up malformed timezone formats
            ts_str = ts_str.replace('+00:00', '+00:00').replace('.87:00', '+00:00')
            # Remove timezone for simple parsing
            if '+' in ts_str:
                ts_str = ts_str.split('+')[0]
            timestamp = datetime.fromisoformat(ts_str)

            # Check if this starts a new session
            if last_timestamp and (timestamp - last_timestamp).seconds > session_gap_minutes * 60:
                # Save current session
                if current_session:
                    session_count += 1
                    session_text = self._format_session(current_session, session_count)
                    conversation_parts.append(session_text)
                    current_session = []

            current_session.append({
                'time': record.get('local_time', timestamp.strftime('%H:%M')),
                'text': record['transcription']
            })
            last_timestamp = timestamp

        # Add final session
        if current_session:
            session_count += 1
            session_text = self._format_session(current_session, session_count)
            conversation_parts.append(session_text)

        # Join all sessions
        full_conversation = "\n\n---\n\n".join(conversation_parts)

        logger.info(f"Combined {len(records)} recordings into {session_count} sessions")
        return full_conversation

    def _format_session(self, session_records: List[Dict], session_num: int) -> str:
        """
        Format a session of recordings

        Args:
            session_records: List of recordings in a session
            session_num: Session number

        Returns:
            Formatted session text
        """
        lines = [f"[Session {session_num}]"]

        for record in session_records:
            time_str = record['time']
            text = record['text']

            # Add timestamp and text
            lines.append(f"[{time_str}] {text}")

        return "\n".join(lines)

    async def get_device_list(self, user_id: Optional[str] = None) -> List[str]:
        """
        Get list of available devices

        Args:
            user_id: Optional user ID to filter devices

        Returns:
            List of device IDs
        """
        try:
            query = self.supabase.table('user_devices')\
                .select('device_id')

            if user_id:
                query = query.eq('user_id', user_id)

            response = query.execute()

            if not response.data:
                return []

            device_ids = [record['device_id'] for record in response.data]
            logger.info(f"Found {len(device_ids)} devices")
            return device_ids

        except Exception as e:
            logger.error(f"Error fetching device list: {str(e)}")
            return []